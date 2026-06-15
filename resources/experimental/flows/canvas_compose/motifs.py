"""Motif library for the canvas-first composer.

A motif is anything that implements `.paint(rgba, rng)`.  Each one paints
across the full 2048x2048 canvas (or a sub-region of it).  Motifs are
intentionally *bold* and *singular* per call -- the forensic study showed
that MINA's skins read at a distance because they place ONE strong feature
per panel, not a haze of subtle ones.

Motifs included
---------------
Stage 0 set (foundational):
    Gradient            : large-scale linear or radial colour stops
    CarbonFiber         : twill-weave background pattern
    BrushStreaks        : long aurora/curtain/caustic shafts
    Galaxy              : FBM nebula + bright star points
    MarbleSwirl         : domain-warped two-tone swirl

Stage 1 set (the 8 building blocks for the 18 deep-research skins):
    Voronoi             : F1/F2 cellular tessellation (crystal facets,
                          snowflake obsidian, bismuth dendrites)
    StarSplat           : low-discrepancy bright points with starburst
                          rays (solar prominence, cyanotype constellations)
    Streamline          : flow-field integrated streaks (Schlieren,
                          cymatics, damascus billet folds)
    ConcentricRings     : multi-centre sin-modulated rings (Iznik tile,
                          brake-disc temper rings, Newton's rings)
    Halftone            : pop-art dot grid with size proportional to
                          source luminance (Memphis, Riso, op-art)
    ReactionDiffusion   : Gray-Scott Turing patterns (organic spots,
                          dendrites, verdigris patina)
    MandalaRadial       : N-fold rotational symmetry of any source
                          (Thangka, Iznik, kaleidoscope)
    Silhouette          : procedural stamps (botanical leaves, hex
                          tiles, stars) for Boro stencil / cyanotype

The implementations rely only on numpy + scipy + PIL filters, so they
run in fractions of a second at 2048^2.  The ReactionDiffusion motif
runs internally at a smaller grid and upsamples.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageFilter

from .composer import Motif

# ---------------------------------------------------------------------------
# Shared helpers (kept local to this module to avoid pulling in legacy code).
# ---------------------------------------------------------------------------


def _stops_to_lut(stops: Sequence[Tuple[float, Tuple[int, int, int]]],
                  n: int = 1024) -> np.ndarray:
    """Convert (position, colour) stops into an Nx3 uint8 colour lookup table."""
    stops = sorted(stops, key=lambda s: s[0])
    xs = np.array([s[0] for s in stops], dtype=np.float64)
    ys = np.array([s[1] for s in stops], dtype=np.float64)
    t = np.linspace(0.0, 1.0, n)
    lut = np.zeros((n, 3), dtype=np.float64)
    for c in range(3):
        lut[:, c] = np.interp(t, xs, ys[:, c])
    return np.clip(lut, 0, 255).astype(np.uint8)


def _gaussian_blur_np(arr: np.ndarray, radius: float) -> np.ndarray:
    """Blur an HxW (or HxWx3) numpy array using PIL's optimised Gaussian."""
    if arr.ndim == 2:
        img = Image.fromarray(arr.astype(np.uint8), "L")
    else:
        img = Image.fromarray(arr.astype(np.uint8), "RGB")
    return np.array(img.filter(ImageFilter.GaussianBlur(radius=radius)))


def _fbm(rng: np.random.Generator, shape: Tuple[int, int],
         octaves: int = 5, lacunarity: float = 2.0,
         gain: float = 0.55) -> np.ndarray:
    """Cheap multi-octave value noise.  Returns float array in [0, 1]."""
    H, W = shape
    accum = np.zeros((H, W), dtype=np.float32)
    norm = 0.0
    amp = 1.0
    for o in range(octaves):
        scale = max(2, int(min(H, W) / (2 ** (o + 2))))
        # Random coarse grid + bilinear upsample (cheap and serviceable).
        nh = max(2, H // scale + 1)
        nw = max(2, W // scale + 1)
        grid = rng.random((nh, nw), dtype=np.float32)
        layer = np.array(Image.fromarray((grid * 255).astype(np.uint8))
                         .resize((W, H), Image.BICUBIC)) / 255.0
        accum += layer * amp
        norm += amp
        amp *= gain
    return accum / max(norm, 1e-6)


# ---------------------------------------------------------------------------
# Gradient
# ---------------------------------------------------------------------------


@dataclass
class Gradient(Motif):
    """A bold large-scale gradient -- linear (default) or radial.

    Parameters
    ----------
    stops : list[(t, (R,G,B))]
        Colour stops with t in [0, 1].  Mapped to the gradient axis.
    direction : str
        "vertical", "horizontal", "diagonal", or "radial".
    radial_center : (cx, cy)
        Used when direction == "radial".  Coordinates in canvas pixels.
    """
    stops: Sequence[Tuple[float, Tuple[int, int, int]]] = field(default_factory=list)
    direction: str = "vertical"
    radial_center: Tuple[int, int] = (1024, 1024)
    name: str = "Gradient"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        lut = _stops_to_lut(list(self.stops) or [(0, (5, 5, 12)), (1, (255, 255, 255))])
        if self.direction == "horizontal":
            t = np.linspace(0, 1, W, dtype=np.float32)
            t = np.broadcast_to(t, (H, W))
        elif self.direction == "diagonal":
            yy = np.linspace(0, 1, H, dtype=np.float32)[:, None]
            xx = np.linspace(0, 1, W, dtype=np.float32)[None, :]
            t = (yy + xx) * 0.5
        elif self.direction == "radial":
            cx, cy = self.radial_center
            yy = np.arange(H, dtype=np.float32)[:, None] - cy
            xx = np.arange(W, dtype=np.float32)[None, :] - cx
            r = np.sqrt(yy * yy + xx * xx)
            t = np.clip(r / max(W, H) * 1.4, 0, 1)
        else:  # vertical
            t = np.linspace(0, 1, H, dtype=np.float32)[:, None]
            t = np.broadcast_to(t, (H, W))
        idx = np.clip((t * (lut.shape[0] - 1)).astype(np.int32), 0, lut.shape[0] - 1)
        rgba[..., :3] = lut[idx]


# ---------------------------------------------------------------------------
# Carbon-fibre weave
# ---------------------------------------------------------------------------


@dataclass
class CarbonFiber(Motif):
    """A 2x2 twill-weave carbon-fibre overlay, blended over the canvas.

    Uses a small repeating tile so the weave is crisp at car-scale.
    Blend = multiply by (0.6 .. 1.0) so it darkens the base without
    overwriting hue.
    """
    tile_px: int = 12
    contrast: float = 0.4    # 0 = invisible, 1 = pure black-on-white
    opacity: float = 0.65
    name: str = "CarbonFiber"

    def _tile(self) -> np.ndarray:
        t = self.tile_px
        tile = np.full((t * 2, t * 2), 0.78, dtype=np.float32)
        # Top-left + bottom-right squares are the "thread highlight".
        tile[:t, :t] = 0.95
        tile[t:, t:] = 0.95
        # Add a tiny dark gutter to give threads a 3D feel.
        tile[t - 1:t + 1, :] = 0.55
        tile[:, t - 1:t + 1] = 0.55
        return tile

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        tile = self._tile()
        ny = math.ceil(H / tile.shape[0])
        nx = math.ceil(W / tile.shape[1])
        big = np.tile(tile, (ny, nx))[:H, :W]
        # Remap to [1-contrast .. 1.0] then blend (multiply).
        factor = (1.0 - self.contrast) + self.contrast * big
        keep = 1.0 - self.opacity
        rgb = rgba[..., :3].astype(np.float32)
        rgba[..., :3] = np.clip(rgb * (keep + self.opacity * factor[..., None]), 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Brush streaks (Aurora curtains, ocean caustics, racing slashes...)
# ---------------------------------------------------------------------------


@dataclass
class BrushStreaks(Motif):
    """Long flowing brush streaks across the canvas.

    Parameters
    ----------
    palette : list of (R,G,B)
        Pool of colours; each streak picks one at random.
    count : int
        Number of streaks.  Big features use 6-12, atmospheric layers 20-40.
    width : (lo, hi)
        Streak thickness range in pixels.
    direction : "vertical" | "horizontal" | "wave"
    wave_amplitude : float
        Pixel amplitude of the sine wave when direction == "wave".
    opacity : float
        Per-streak opacity in [0, 1].
    """
    palette: Sequence[Tuple[int, int, int]] = field(default_factory=list)
    count: int = 12
    width: Tuple[int, int] = (30, 120)
    direction: str = "vertical"
    wave_amplitude: float = 80.0
    opacity: float = 0.8
    name: str = "BrushStreaks"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        if not self.palette:
            return
        # Build a HxW float canvas for accumulating colour additively, then
        # composite at the end so overlapping streaks brighten naturally.
        accum_rgb = np.zeros((H, W, 3), dtype=np.float32)
        accum_alpha = np.zeros((H, W), dtype=np.float32)

        for _ in range(self.count):
            colour = np.array(self.palette[int(rng.integers(0, len(self.palette)))],
                              dtype=np.float32)
            w = int(rng.integers(self.width[0], self.width[1] + 1))
            if self.direction == "horizontal":
                cy = int(rng.integers(0, H))
                yy = np.arange(H, dtype=np.float32)[:, None]
                d = np.abs(yy - cy)
                d = np.broadcast_to(d, (H, W))
            elif self.direction == "wave":
                cx = int(rng.integers(0, W))
                freq = float(rng.uniform(0.0015, 0.004))
                phase = float(rng.uniform(0, 2 * math.pi))
                yy = np.arange(H, dtype=np.float32)
                offsets = self.wave_amplitude * np.sin(yy * freq + phase)
                centers = cx + offsets
                xx = np.arange(W, dtype=np.float32)[None, :]
                d = np.abs(xx - centers[:, None])
            else:  # vertical
                cx = int(rng.integers(0, W))
                xx = np.arange(W, dtype=np.float32)[None, :]
                d = np.abs(xx - cx)
                d = np.broadcast_to(d, (H, W))
            # Smooth falloff
            falloff = np.clip(1.0 - d / float(w), 0.0, 1.0) ** 1.6
            # Random per-streak length taper -- so streaks don't all reach edges.
            if self.direction in ("vertical", "wave"):
                t_start = float(rng.uniform(0.0, 0.25))
                t_end = float(rng.uniform(0.75, 1.0))
                yy_n = np.linspace(0, 1, H, dtype=np.float32)
                taper = np.clip((yy_n - t_start) * (t_end - yy_n) * 16.0, 0.0, 1.0)
                falloff *= taper[:, None]
            elif self.direction == "horizontal":
                t_start = float(rng.uniform(0.0, 0.25))
                t_end = float(rng.uniform(0.75, 1.0))
                xx_n = np.linspace(0, 1, W, dtype=np.float32)
                taper = np.clip((xx_n - t_start) * (t_end - xx_n) * 16.0, 0.0, 1.0)
                falloff *= taper[None, :]
            a = falloff * self.opacity
            accum_rgb += colour[None, None, :] * a[..., None]
            accum_alpha = np.maximum(accum_alpha, a)

        # Soft-blur the result so the streaks read as painterly instead of CG.
        accum_rgb = _gaussian_blur_np(np.clip(accum_rgb, 0, 255), radius=3.0)
        a = accum_alpha[..., None]
        rgb = rgba[..., :3].astype(np.float32)
        rgba[..., :3] = np.clip(rgb * (1 - a) + accum_rgb * a, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Galaxy / nebula
# ---------------------------------------------------------------------------


@dataclass
class Galaxy(Motif):
    """FBM-based nebula with bright star points.

    Parameters
    ----------
    palette : list of (R,G,B)
        Coloured nebula gases (typically 3-5 colours from indigo->magenta).
    star_count : int
        Number of bright pinpoints scattered across the canvas.
    nebula_strength : float in [0,1]
        How strongly the nebula overwrites the base.
    """
    palette: Sequence[Tuple[int, int, int]] = field(default_factory=list)
    star_count: int = 1400
    nebula_strength: float = 0.95
    name: str = "Galaxy"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        if not self.palette:
            return
        # 1) Two-band FBM, one for density, one for hue selection.
        density = _fbm(rng, (H, W), octaves=6, gain=0.55)
        hue_sel = _fbm(rng, (H, W), octaves=4, gain=0.55)

        # Heavy bias so most of the canvas is dark and only ribbons glow.
        density = np.clip((density - 0.45) * 3.0, 0.0, 1.0) ** 1.4

        # 2) Quantise hue_sel into the palette.
        n_cols = len(self.palette)
        idx = np.clip((hue_sel * n_cols).astype(np.int32), 0, n_cols - 1)
        palette = np.array(self.palette, dtype=np.float32)
        col_map = palette[idx]            # (H,W,3)

        # 3) Composite nebula over base.
        a = (density * self.nebula_strength)[..., None]
        rgb = rgba[..., :3].astype(np.float32)
        rgba[..., :3] = np.clip(rgb * (1 - a) + col_map * a, 0, 255).astype(np.uint8)

        # 4) Sprinkle stars: random pixels with bright RGB, with rare big ones.
        ys = rng.integers(0, H, size=self.star_count)
        xs = rng.integers(0, W, size=self.star_count)
        # Brightness pulled from a heavy-tail distribution.
        b = rng.beta(0.8, 4.0, size=self.star_count) * 255 + 30
        b = np.clip(b, 0, 255).astype(np.uint8)
        rgba[ys, xs, 0] = np.maximum(rgba[ys, xs, 0], b)
        rgba[ys, xs, 1] = np.maximum(rgba[ys, xs, 1], b)
        rgba[ys, xs, 2] = np.maximum(rgba[ys, xs, 2], b)
        # A few large stars with soft halo (sample 1.5% as "big").
        big_n = max(1, int(self.star_count * 0.015))
        for i in rng.integers(0, self.star_count, size=big_n):
            y, x = int(ys[i]), int(xs[i])
            r = int(rng.integers(2, 6))
            y0, y1 = max(0, y - r), min(H, y + r + 1)
            x0, x1 = max(0, x - r), min(W, x + r + 1)
            patch = rgba[y0:y1, x0:x1, :3].astype(np.float32)
            patch = np.maximum(patch, 200)
            rgba[y0:y1, x0:x1, :3] = patch.astype(np.uint8)


# ---------------------------------------------------------------------------
# Marble swirl
# ---------------------------------------------------------------------------


@dataclass
class MarbleSwirl(Motif):
    """Domain-warped two-tone marble swirl.

    Good for premium / luxury skins (jet black with gold veins, navy with
    pearl veins, etc).
    """
    base_color: Tuple[int, int, int] = (8, 8, 14)
    vein_color: Tuple[int, int, int] = (210, 180, 90)
    vein_threshold: float = 0.58
    vein_softness: float = 0.08
    opacity: float = 1.0
    name: str = "MarbleSwirl"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        n1 = _fbm(rng, (H, W), octaves=5, gain=0.6)
        n2 = _fbm(rng, (H, W), octaves=5, gain=0.6)
        warped = _fbm(rng, (H, W), octaves=6, gain=0.55)
        # Domain warp.
        sx = (n1 - 0.5) * 60
        sy = (n2 - 0.5) * 60
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        wy = np.clip(yy + sy, 0, H - 1).astype(np.int32)
        wx = np.clip(xx + sx, 0, W - 1).astype(np.int32)
        veins = warped[wy, wx]
        # Soft band around threshold = the vein.
        d = np.abs(veins - self.vein_threshold)
        mask = np.clip(1.0 - d / self.vein_softness, 0.0, 1.0) ** 1.4
        base = np.array(self.base_color, dtype=np.float32)
        vein = np.array(self.vein_color, dtype=np.float32)
        out = base[None, None, :] * (1 - mask[..., None]) + vein[None, None, :] * mask[..., None]
        if float(self.opacity) >= 0.999:
            rgba[..., :3] = np.clip(out, 0, 255).astype(np.uint8)
        else:
            a = float(self.opacity)
            base_canvas = rgba[..., :3].astype(np.float32)
            rgba[..., :3] = np.clip(base_canvas * (1.0 - a) + out * a,
                                     0, 255).astype(np.uint8)


# ===========================================================================
# Stage 1 motif set -- the 8 building blocks for the 18 deep-research skins.
# ===========================================================================


def _composite_rgb(rgba: np.ndarray, layer_rgb: np.ndarray,
                   alpha: np.ndarray) -> None:
    """In-place compositing of a float RGB layer onto rgba using float alpha.

    `layer_rgb` is (H, W, 3) float [0,255]; `alpha` is (H, W) float [0, 1].
    """
    a = alpha[..., None]
    base = rgba[..., :3].astype(np.float32)
    rgba[..., :3] = np.clip(base * (1.0 - a) + layer_rgb * a, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# 1. Voronoi -- cellular tessellation
# ---------------------------------------------------------------------------


@dataclass
class Voronoi(Motif):
    """Voronoi tessellation with optional F1/F2 ridge rendering.

    Each cell is filled with a colour from `palette`.  Optional ridge:
    the F1-F2 difference (distance to nearest site minus distance to the
    second-nearest) produces sharp lines along cell boundaries -- great
    for crystal facets / bismuth / snowflake-obsidian.

    Parameters
    ----------
    palette : list of (R,G,B)
        Cell colours; sampled per-site.
    n_sites : int
        Number of generator points.  100-300 reads as crystals at car
        distance; 500-1500 reads as fine cellular texture.
    ridge : float in [0,1]
        How much to darken (ridge>0) or brighten (ridge<0) cell
        boundaries.  0 = flat cells, 1 = strong crisp ridges.
    ridge_width : int
        Pixel width of the ridge band.
    jitter : float in [0,1]
        How much to perturb sites off a regular grid.  1.0 = pure random.
    """
    palette: Sequence[Tuple[int, int, int]] = field(default_factory=list)
    n_sites: int = 220
    ridge: float = 0.55
    ridge_width: int = 6
    jitter: float = 1.0
    opacity: float = 1.0
    name: str = "Voronoi"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        from scipy.spatial import cKDTree
        H, W, _ = rgba.shape
        if not self.palette:
            return

        # Place sites: jitter on a grid for "natural-but-even" spacing.
        n_rows = int(round(math.sqrt(self.n_sites * H / W)))
        n_cols = max(1, int(round(self.n_sites / max(1, n_rows))))
        ys = np.linspace(0, H - 1, n_rows + 2)[1:-1]
        xs = np.linspace(0, W - 1, n_cols + 2)[1:-1]
        gx, gy = np.meshgrid(xs, ys)
        sites = np.stack([gx.ravel(), gy.ravel()], axis=1)
        if self.jitter > 0:
            dx = (rng.random(sites.shape[0]) - 0.5) * (W / max(1, n_cols)) * self.jitter
            dy = (rng.random(sites.shape[0]) - 0.5) * (H / max(1, n_rows)) * self.jitter
            sites = sites + np.stack([dx, dy], axis=1)

        tree = cKDTree(sites)
        # Sample 1-out-of-2 pixels for speed, then bilinearly upscale labels.
        # 2048x2048 = 4M queries; KDTree k=2 takes ~2s.  Use full resolution
        # for fidelity.
        yy, xx = np.mgrid[0:H, 0:W]
        coords = np.stack([xx.ravel(), yy.ravel()], axis=1)
        d, idx = tree.query(coords, k=2)
        d1 = d[:, 0].reshape(H, W)
        d2 = d[:, 1].reshape(H, W)
        labels = idx[:, 0].reshape(H, W)

        palette = np.array(self.palette, dtype=np.float32)
        col_idx = rng.integers(0, len(palette), size=sites.shape[0])
        cell_rgb = palette[col_idx[labels]]  # (H, W, 3)

        if self.ridge > 0:
            ridge_signal = np.clip((d2 - d1) / max(1, self.ridge_width), 0, 1)
            # ridge_signal is ~1 inside cells, drops to 0 on boundary.
            darken = (1.0 - ridge_signal) ** 1.6
            cell_rgb = cell_rgb * (1.0 - darken[..., None] * self.ridge)
        elif self.ridge < 0:
            ridge_signal = np.clip((d2 - d1) / max(1, self.ridge_width), 0, 1)
            brighten = (1.0 - ridge_signal) ** 1.6
            cell_rgb = cell_rgb + (255 - cell_rgb) * (brighten[..., None] * (-self.ridge))

        if float(self.opacity) >= 0.999:
            rgba[..., :3] = np.clip(cell_rgb, 0, 255).astype(np.uint8)
        else:
            a = float(self.opacity)
            base_canvas = rgba[..., :3].astype(np.float32)
            rgba[..., :3] = np.clip(base_canvas * (1.0 - a) + cell_rgb * a,
                                     0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# 2. StarSplat -- low-discrepancy bright points with starburst rays
# ---------------------------------------------------------------------------


def _halton(i: int, base: int) -> float:
    """i-th Halton-sequence value in base `base`.  Used for low-discrepancy
    point placement that looks "evenly random" without clustering."""
    f, r = 1.0, 0.0
    while i > 0:
        f /= base
        r += f * (i % base)
        i //= base
    return r


@dataclass
class StarSplat(Motif):
    """Bright stars drawn with gaussian halo + 4-ray starburst.

    Foundation motif for solar prominences (large flares) and cyanotype
    constellations (small precise stars).  Uses a Halton sequence so the
    points feel random but cover the canvas evenly.

    Parameters
    ----------
    palette : list of (R,G,B)
        Star colours (typically 1-3 hot/cool variants).
    count : int
        Number of stars.
    size_range : (lo, hi)
        Half-width of star halo in pixels.
    ray_length : int
        Length of the four cross rays in pixels.  0 = pure halo.
    intensity : float in [0,1]
        Peak brightness relative to canvas (1.0 = full white).
    halton_seed : int
        Offset into the Halton sequence -- gives variation without losing
        the even-coverage property.
    """
    palette: Sequence[Tuple[int, int, int]] = field(default_factory=list)
    count: int = 300
    size_range: Tuple[int, int] = (8, 28)
    ray_length: int = 36
    intensity: float = 0.85
    halton_seed: int = 17
    name: str = "StarSplat"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        if not self.palette:
            return
        palette = np.array(self.palette, dtype=np.float32)
        # Per-pixel max-weight (so overlapping stars stay believable -- one
        # bright star, not a glow-bomb).  Per-star colour is blended into a
        # parallel RGB buffer using the same weight, so the final composite
        # picks the dominant star at each pixel.
        weight_max = np.zeros((H, W), dtype=np.float32)
        layer_rgb = np.zeros((H, W, 3), dtype=np.float32)
        for i in range(self.count):
            x = int(_halton(self.halton_seed + i + 1, 2) * W)
            y = int(_halton(self.halton_seed + i + 1, 3) * H)
            r = int(rng.integers(self.size_range[0], self.size_range[1] + 1))
            colour = palette[int(rng.integers(0, len(palette)))]
            # Compact halo: 2-sigma rather than 3, so neighbouring stars
            # don't merge into a single blob.
            pad = max(2, int(r * 2))
            y0, y1 = max(0, y - pad), min(H, y + pad + 1)
            x0, x1 = max(0, x - pad), min(W, x + pad + 1)
            yy = (np.arange(y0, y1) - y).astype(np.float32)
            xx = (np.arange(x0, x1) - x).astype(np.float32)
            dy = yy[:, None]
            dx = xx[None, :]
            d2 = dx * dx + dy * dy
            halo = np.exp(-d2 / (2.0 * r * r))
            # Sharp central "core" so each star reads as a point, not a haze.
            core = np.exp(-d2 / 1.6) * 0.9
            if self.ray_length > 0:
                ray = (np.exp(-(dx * dx) / 1.5)
                       * np.clip(1 - np.abs(dy) / self.ray_length, 0, 1)
                       * 0.45)
                ray += (np.exp(-(dy * dy) / 1.5)
                        * np.clip(1 - np.abs(dx) / self.ray_length, 0, 1)
                        * 0.45)
                weight = np.maximum(np.maximum(halo, ray), core)
            else:
                weight = np.maximum(halo, core)
            sub = weight_max[y0:y1, x0:x1]
            new_max = np.maximum(sub, weight)
            mask = new_max > sub + 1e-6
            if mask.any():
                layer_rgb[y0:y1, x0:x1][mask] = colour
            weight_max[y0:y1, x0:x1] = new_max
        a = np.clip(weight_max * self.intensity, 0, 1)
        _composite_rgb(rgba, layer_rgb, a)


# ---------------------------------------------------------------------------
# 3. Streamline -- integrate strokes along an FBM vector field
# ---------------------------------------------------------------------------


@dataclass
class Streamline(Motif):
    """Long flowing streaks following a procedural vector field.

    Builds an angle field from FBM noise (or radial / linear flow if
    `field_mode` differs), then RK1-integrates `n_lines` short segments
    from random seeds, stamping a soft brush along the trace.

    Foundation motif for Schlieren visualisations, cymatic patterns,
    Damascus billet folds, oil-slick refraction lines.

    Parameters
    ----------
    palette : list of (R,G,B)
        Brush colours.
    n_lines : int
        Number of streamline traces.  600-2000 dense, 100-300 sparse.
    line_length : int
        Number of integration steps per line.
    line_step : float
        Pixels per step.
    line_thickness : float
        Brush radius in pixels.
    field_mode : "fbm" | "radial" | "linear" | "swirl"
        How to generate the vector field.
    field_scale : float
        How "wavy" the FBM field is (smaller = tighter swirls).
    field_angle_deg : float
        Bias angle for "linear" mode; centre for "radial"/"swirl".
    opacity : float in [0,1]
        Stroke opacity.
    """
    palette: Sequence[Tuple[int, int, int]] = field(default_factory=list)
    n_lines: int = 900
    line_length: int = 220
    line_step: float = 2.5
    line_thickness: float = 2.4
    field_mode: str = "fbm"
    field_scale: float = 1.0
    field_angle_deg: float = 0.0
    field_center: Optional[Tuple[float, float]] = None
    opacity: float = 0.6
    name: str = "Streamline"

    def _field(self, shape: Tuple[int, int],
               rng: np.random.Generator) -> np.ndarray:
        H, W = shape
        if self.field_mode == "linear":
            theta = math.radians(self.field_angle_deg)
            return np.full((H, W), theta, dtype=np.float32)
        # Centre for radial / swirl modes.  Defaults to canvas centre;
        # ``field_center`` lets callers re-origin the field at any (x, y)
        # pixel coordinate -- useful for second radial passes targeting
        # off-axis UV islands (e.g. NOSE @ (532, 1824)) so the burst
        # visually converges between body panels.
        if self.field_center is not None:
            cx, cy = float(self.field_center[0]), float(self.field_center[1])
        else:
            cx, cy = W * 0.5, H * 0.5
        if self.field_mode == "radial":
            yy = np.arange(H, dtype=np.float32)[:, None] - cy
            xx = np.arange(W, dtype=np.float32)[None, :] - cx
            return np.arctan2(yy, xx).astype(np.float32)
        if self.field_mode == "swirl":
            yy = np.arange(H, dtype=np.float32)[:, None] - cy
            xx = np.arange(W, dtype=np.float32)[None, :] - cx
            return (np.arctan2(yy, xx) + math.pi / 2).astype(np.float32)
        # default: FBM-driven angle in [-pi, pi]
        n = _fbm(rng, shape, octaves=5, gain=0.55)
        return ((n - 0.5) * (2 * math.pi) * self.field_scale).astype(np.float32)

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        if not self.palette:
            return
        palette = np.array(self.palette, dtype=np.float32)
        field_arr = self._field((H, W), rng)

        accum_rgb = np.zeros((H, W, 3), dtype=np.float32)
        accum_a = np.zeros((H, W), dtype=np.float32)

        r = self.line_thickness
        rad = int(math.ceil(r) + 1)
        # Precompute brush stamp (radial gauss).
        yy = np.arange(-rad, rad + 1, dtype=np.float32)
        brush = np.exp(-(yy[:, None] ** 2 + yy[None, :] ** 2) / (2 * r * r))

        for _ in range(self.n_lines):
            # Random seed point.
            x = float(rng.uniform(0, W))
            y = float(rng.uniform(0, H))
            colour = palette[int(rng.integers(0, len(palette)))]
            for step in range(self.line_length):
                ix, iy = int(x), int(y)
                if not (0 <= ix < W and 0 <= iy < H):
                    break
                theta = float(field_arr[iy, ix])
                # Stamp brush.
                y0, y1 = max(0, iy - rad), min(H, iy + rad + 1)
                x0, x1 = max(0, ix - rad), min(W, ix + rad + 1)
                by0 = y0 - (iy - rad); by1 = by0 + (y1 - y0)
                bx0 = x0 - (ix - rad); bx1 = bx0 + (x1 - x0)
                stamp = brush[by0:by1, bx0:bx1]
                accum_rgb[y0:y1, x0:x1] += colour[None, None, :] * stamp[..., None]
                accum_a[y0:y1, x0:x1] = np.maximum(accum_a[y0:y1, x0:x1], stamp)
                # Advance.
                x += self.line_step * math.cos(theta)
                y += self.line_step * math.sin(theta)

        # Normalise additive RGB by accumulated alpha.
        norm = np.maximum(accum_a[..., None] * 8.0, 1.0)
        accum_rgb = np.clip(accum_rgb / norm, 0, 255)
        a = np.clip(accum_a * self.opacity, 0, 1)
        _composite_rgb(rgba, accum_rgb, a)


# ---------------------------------------------------------------------------
# 4. ConcentricRings -- multi-centre sin-modulated rings
# ---------------------------------------------------------------------------


@dataclass
class ConcentricRings(Motif):
    """Multiple ring centres composited together.

    For each centre we compute ``sin(2*pi*r/wavelength + phase)``, threshold
    into bright bands, and add into the canvas.  When several centres overlap
    you get Newton's-rings / sound-interference patterns -- great for Iznik
    tile motifs, cymatic plates, brake-disc temper rings, wave physics
    diagrams.

    Parameters
    ----------
    palette : list of (R,G,B)
        Ring colours; one per centre, or cycled if fewer than `n_centres`.
    n_centres : int
        Number of ring origins.
    centres : list of (x, y) or None
        Explicit centres in pixel coords; if None, sampled randomly.
    wavelength : float
        Pixels between consecutive bright rings.
    band_width : float in [0,1]
        Fraction of each wavelength that is "bright".  0.1 = thin lines,
        0.5 = thick bands.
    decay : float in (0, 4)
        Radial decay of ring brightness; higher = rings fade faster.
    opacity : float in [0,1]
        Final blend opacity.
    """
    palette: Sequence[Tuple[int, int, int]] = field(default_factory=list)
    n_centres: int = 6
    centres: Optional[Sequence[Tuple[int, int]]] = None
    wavelength: float = 80.0
    band_width: float = 0.22
    decay: float = 0.8
    opacity: float = 0.85
    name: str = "ConcentricRings"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        if not self.palette:
            return
        palette = np.array(self.palette, dtype=np.float32)
        centres = self.centres
        if not centres:
            centres = [(int(rng.uniform(W * 0.1, W * 0.9)),
                        int(rng.uniform(H * 0.1, H * 0.9)))
                       for _ in range(self.n_centres)]
        accum_rgb = np.zeros((H, W, 3), dtype=np.float32)
        accum_a = np.zeros((H, W), dtype=np.float32)
        yy = np.arange(H, dtype=np.float32)[:, None]
        xx = np.arange(W, dtype=np.float32)[None, :]
        diag = math.hypot(W, H)
        for i, (cx, cy) in enumerate(centres):
            colour = palette[i % len(palette)]
            r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            phase = (r / max(1e-3, self.wavelength)) % 1.0
            band = (np.abs(phase - 0.5) < self.band_width * 0.5).astype(np.float32)
            soft = np.clip(1.0 - np.abs(phase - 0.5) / self.band_width, 0, 1) ** 0.8
            band = np.maximum(band * 0.7, soft * 0.5)
            # Distance decay.
            decay = np.exp(-(r / diag) * self.decay * 4.0)
            ring = band * decay
            accum_rgb += colour[None, None, :] * ring[..., None]
            accum_a = np.maximum(accum_a, ring)
        accum_rgb = np.clip(accum_rgb, 0, 255)
        a = np.clip(accum_a * self.opacity, 0, 1)
        _composite_rgb(rgba, accum_rgb, a)


# ---------------------------------------------------------------------------
# 5. Halftone -- pop-art dot grid sized by source luminance
# ---------------------------------------------------------------------------


@dataclass
class Halftone(Motif):
    """Pop-art halftone dots painted over the existing canvas.

    For each cell of size `cell_px`, samples the source canvas luminance,
    and draws a dot whose radius scales with darkness.  Optional rotation
    of the cell grid produces classic CMY-K halftone screens.

    Use over a strong gradient or photograph to get a comic / Lichtenstein
    feel; on top of a Riso scan, gives the unmistakable risograph dot.

    Parameters
    ----------
    dot_color : (R,G,B)
        Colour of the dots.
    cell_px : int
        Cell size in pixels.  20-40 reads as halftone at car distance.
    angle_deg : float
        Rotation of the cell grid (15-deg increments for classic CMYK).
    invert : bool
        If True, dot radius scales with luminance (bright -> big dot).
        Default False = dark -> big dot.
    min_radius_frac : float
        Smallest dot radius as a fraction of the cell size.
    max_radius_frac : float
        Largest dot radius as a fraction of the cell size.
    """
    dot_color: Tuple[int, int, int] = (16, 16, 22)
    cell_px: int = 28
    angle_deg: float = 15.0
    invert: bool = False
    min_radius_frac: float = 0.0
    max_radius_frac: float = 0.48
    opacity: float = 0.95
    name: str = "Halftone"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        # Source luminance.
        src = rgba[..., :3].astype(np.float32)
        lum = 0.2126 * src[..., 0] + 0.7152 * src[..., 1] + 0.0722 * src[..., 2]
        if self.invert:
            t = np.clip(lum / 255.0, 0, 1)
        else:
            t = np.clip(1.0 - lum / 255.0, 0, 1)
        # Sample a grid of cells; per-cell, average luminance -> dot radius.
        c = max(2, self.cell_px)
        # Rotate the (yy, xx) coordinates so dots fall on the rotated grid.
        theta = math.radians(self.angle_deg)
        ct, st = math.cos(theta), math.sin(theta)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        u = (xx * ct + yy * st) / c
        v = (-xx * st + yy * ct) / c
        # Cell index = floor(u, v); cell centre at (u+0.5, v+0.5).
        cu = np.floor(u) + 0.5
        cv = np.floor(v) + 0.5
        # Sample t at cell centres.  Inverse-rotate to get canvas coords.
        sxc = (cu * ct - cv * st) * c
        syc = (cu * st + cv * ct) * c
        sxi = np.clip(sxc.astype(np.int32), 0, W - 1)
        syi = np.clip(syc.astype(np.int32), 0, H - 1)
        tc = t[syi, sxi]
        # Radius per pixel from the cell's t value.
        rmin = self.min_radius_frac * c
        rmax = self.max_radius_frac * c
        radius = rmin + (rmax - rmin) * tc
        # Distance from pixel to its cell centre (in rotated coords).
        du = (u - cu) * c
        dv = (v - cv) * c
        dist = np.sqrt(du * du + dv * dv)
        # Soft edge so dots don't alias.
        dot = np.clip(radius - dist, 0.0, 1.0)
        dot = (dot ** 1.5)
        a = dot * self.opacity
        colour = np.array(self.dot_color, dtype=np.float32)
        layer = np.broadcast_to(colour, (H, W, 3))
        _composite_rgb(rgba, layer, a)


# ---------------------------------------------------------------------------
# 6. ReactionDiffusion -- Gray-Scott Turing patterns
# ---------------------------------------------------------------------------


@dataclass
class ReactionDiffusion(Motif):
    """Gray-Scott reaction-diffusion patterns (Turing morphogen).

    Simulates two chemicals `U` and `V` on a 2D grid under the system:

        dU/dt = Du * laplacian(U) - U*V*V + F*(1 - U)
        dV/dt = Dv * laplacian(V) + U*V*V - (F + k)*V

    Choosing (F, k) within a narrow window produces stable patterns:
    spots, stripes, mazes, dendrites, "coral", "spirals".

    Computed at low resolution (`grid_size`) then bicubic-upscaled to
    2048x2048 -- the patterns are inherently smooth so this looks fine.

    Parameters
    ----------
    palette_low : (R,G,B)
        Colour where V is low (the "background" chemical).
    palette_high : (R,G,B)
        Colour where V is high (the "spots/stripes" chemical).
    F : float
        Feed rate.  0.022 (coral), 0.030 (spots), 0.039 (mazes), 0.055 (spirals).
    k : float
        Kill rate.  0.051..0.062.  See pattern atlas in docstring.
    grid_size : int
        Simulation resolution (256-512 recommended; runs O(steps * N^2)).
    steps : int
        Number of integration steps.  4000-10000 for fully formed patterns.
    Du, Dv : float
        Diffusion rates for U, V.
    """
    palette_low: Tuple[int, int, int] = (8, 12, 18)
    palette_high: Tuple[int, int, int] = (220, 200, 170)
    F: float = 0.030
    k: float = 0.062
    grid_size: int = 320
    steps: int = 5000
    Du: float = 0.16
    Dv: float = 0.08
    name: str = "ReactionDiffusion"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        N = max(64, self.grid_size)
        U = np.ones((N, N), dtype=np.float32)
        V = np.zeros((N, N), dtype=np.float32)
        # Seed: a handful of random patches of V.
        n_seeds = int(rng.integers(15, 40))
        for _ in range(n_seeds):
            cy = int(rng.integers(0, N))
            cx = int(rng.integers(0, N))
            r = int(rng.integers(3, 9))
            y0, y1 = max(0, cy - r), min(N, cy + r)
            x0, x1 = max(0, cx - r), min(N, cx + r)
            U[y0:y1, x0:x1] = 0.5
            V[y0:y1, x0:x1] = 0.25

        def laplace(Z: np.ndarray) -> np.ndarray:
            # 5-point stencil with periodic boundaries.
            return (np.roll(Z, 1, 0) + np.roll(Z, -1, 0)
                    + np.roll(Z, 1, 1) + np.roll(Z, -1, 1) - 4 * Z)

        F = self.F
        k = self.k
        Du = self.Du
        Dv = self.Dv
        for _ in range(self.steps):
            uvv = U * V * V
            U += Du * laplace(U) - uvv + F * (1 - U)
            V += Dv * laplace(V) + uvv - (F + k) * V

        # V is in roughly [0, 0.7]; normalise to [0, 1].
        Vn = np.clip(V / max(1e-3, V.max()), 0, 1)
        # Upscale to canvas size with bicubic interpolation.
        H, W, _ = rgba.shape
        Vn_img = Image.fromarray((Vn * 255).astype(np.uint8)).resize(
            (W, H), Image.BICUBIC)
        Vn_full = np.array(Vn_img).astype(np.float32) / 255.0
        low = np.array(self.palette_low, dtype=np.float32)
        high = np.array(self.palette_high, dtype=np.float32)
        out = low[None, None, :] * (1 - Vn_full[..., None]) + \
              high[None, None, :] * Vn_full[..., None]
        rgba[..., :3] = np.clip(out, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# 7. MandalaRadial -- N-fold rotational symmetry of a source pattern
# ---------------------------------------------------------------------------


@dataclass
class MandalaRadial(Motif):
    """Take an FBM/colour source, then enforce N-fold rotational symmetry.

    Each output pixel at polar (r, theta) is sampled from polar
    (r, theta mod (2 pi / n)) in the source.  Optional mirror symmetry
    inside each wedge makes a 2N-fold mandala (Thangka, Iznik tile).

    Parameters
    ----------
    palette : list of (R,G,B)
        Source palette mapped from FBM values.
    n_fold : int
        Number of rotational sectors.  6 / 8 / 12 are common.
    mirror : bool
        If True, also mirror inside each wedge -> 2*N-fold dihedral.
    palette_softness : float
        Smoothing applied to the palette-index field (lower -> sharper
        bands, higher -> smoother gradients).
    radial_taper : float
        How much the central region is brightened/darkened to anchor
        the eye.  0 = uniform, 1 = strong centre highlight.
    """
    palette: Sequence[Tuple[int, int, int]] = field(default_factory=list)
    n_fold: int = 8
    mirror: bool = True
    palette_softness: float = 0.6
    radial_taper: float = 0.3
    name: str = "MandalaRadial"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        if not self.palette:
            return
        cy, cx = H / 2.0, W / 2.0
        yy = np.arange(H, dtype=np.float32)[:, None] - cy
        xx = np.arange(W, dtype=np.float32)[None, :] - cx
        r = np.sqrt(xx * xx + yy * yy)
        theta = np.arctan2(yy, xx)
        # Reduce theta into the canonical wedge.
        wedge = (2 * math.pi) / max(1, self.n_fold)
        canonical = (theta % wedge)
        if self.mirror:
            canonical = np.where(canonical > wedge / 2, wedge - canonical, canonical)
        # Map (r, canonical) -> (sample_x, sample_y) within a source FBM.
        # Stretch the canonical strip to use the full source width.
        u = (canonical / max(1e-6, wedge)) * (W * 0.5)
        v = r
        src_x = np.clip(cx + (u - W * 0.25), 0, W - 1).astype(np.int32)
        src_y = np.clip(cy - W * 0.25 + v, 0, H - 1).astype(np.int32)
        # Build a source FBM and a smooth palette field.
        n = _fbm(rng, (H, W), octaves=5, gain=0.55)
        # Tint by palette via quantised hue-selector.
        palette = np.array(self.palette, dtype=np.float32)
        # Smooth t so the palette transitions feel mandala-like.
        if self.palette_softness > 0:
            n_blur = _gaussian_blur_np((n * 255).astype(np.uint8),
                                        radius=4 + self.palette_softness * 10)
            n = n_blur / 255.0
        # Sample with our symmetry-aware coordinates.
        sampled = n[src_y, src_x]
        idx = np.clip((sampled * len(palette)).astype(np.int32), 0, len(palette) - 1)
        col = palette[idx]
        # Radial taper: brighten / darken the centre.
        if self.radial_taper != 0:
            diag = math.hypot(W, H) * 0.5
            taper = (1.0 - r / diag).clip(0, 1) ** 1.6
            col = col + (np.array([255, 255, 255], np.float32) - col) * \
                  (taper[..., None] * self.radial_taper * 0.4)
        rgba[..., :3] = np.clip(col, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# 8. Silhouette -- stamps of procedural shapes (leaves, hex tiles, stars)
# ---------------------------------------------------------------------------


def _leaf_mask(size: int, rng: np.random.Generator) -> np.ndarray:
    """Procedural botanical leaf silhouette in a (size, size) float mask."""
    s = size
    yy = (np.arange(s, dtype=np.float32) - s / 2) / (s / 2)
    xx = (np.arange(s, dtype=np.float32) - s / 2) / (s / 2)
    # Leaf shape: |y|/(1-x^2) < a; tilt slightly.
    XX, YY = np.meshgrid(xx, yy)
    angle = float(rng.uniform(-0.6, 0.6))
    XR = XX * math.cos(angle) - YY * math.sin(angle)
    YR = XX * math.sin(angle) + YY * math.cos(angle)
    a = float(rng.uniform(0.35, 0.55))
    body = (np.abs(YR) < a * (1 - XR * XR + 1e-3)).astype(np.float32)
    # Veins: faint stripe at y=0.
    vein = np.exp(-(YR * YR) / 0.005) * body * 0.4
    return np.clip(body + vein, 0, 1)


def _hex_mask(size: int) -> np.ndarray:
    """Hexagon silhouette mask."""
    s = size
    yy = np.linspace(-1, 1, s, dtype=np.float32)
    xx = np.linspace(-1, 1, s, dtype=np.float32)
    XX, YY = np.meshgrid(xx, yy)
    h = 0.86  # apothem-to-radius ratio for unit hex
    return ((np.abs(YY) < h) & (np.abs(XX * h + YY * 0.5) < h)
            & (np.abs(XX * h - YY * 0.5) < h)).astype(np.float32)


def _star_mask(size: int, n_points: int = 5) -> np.ndarray:
    """N-pointed star silhouette mask."""
    s = size
    yy = (np.arange(s, dtype=np.float32) - s / 2) / (s / 2)
    xx = (np.arange(s, dtype=np.float32) - s / 2) / (s / 2)
    XX, YY = np.meshgrid(xx, yy)
    r = np.sqrt(XX * XX + YY * YY)
    theta = np.arctan2(YY, XX)
    # Radius modulation -- N petals.
    rho = 0.45 + 0.35 * np.cos(theta * n_points)
    return (r < rho).astype(np.float32)


@dataclass
class Silhouette(Motif):
    """Scatter procedural-shape silhouettes across the canvas.

    `shape` is one of "leaf", "hex", "star", or "circle".  Each stamp is
    placed at a low-discrepancy point, optionally rotated, and tinted
    with a colour from `palette`.  Designed for Boro stencil / cyanotype
    botanical / Memphis confetti looks.

    Parameters
    ----------
    palette : list of (R,G,B)
        Stamp colours.
    shape : str
        "leaf", "hex", "star", "circle".
    count : int
        Number of stamps.
    size_range : (lo, hi)
        Stamp side length in pixels.
    opacity : float
        Per-stamp opacity.
    halton_seed : int
        Offset into Halton point sequence.
    star_points : int
        Number of star points when `shape == "star"`.
    """
    palette: Sequence[Tuple[int, int, int]] = field(default_factory=list)
    shape: str = "leaf"
    count: int = 220
    size_range: Tuple[int, int] = (80, 200)
    opacity: float = 0.85
    halton_seed: int = 23
    star_points: int = 5
    name: str = "Silhouette"

    def _make_stamp(self, size: int, rng: np.random.Generator) -> np.ndarray:
        if self.shape == "hex":
            return _hex_mask(size)
        if self.shape == "star":
            return _star_mask(size, self.star_points)
        if self.shape == "circle":
            yy = (np.arange(size, dtype=np.float32) - size / 2) / (size / 2)
            xx = (np.arange(size, dtype=np.float32) - size / 2) / (size / 2)
            XX, YY = np.meshgrid(xx, yy)
            return (XX * XX + YY * YY < 0.9 ** 2).astype(np.float32)
        return _leaf_mask(size, rng)

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        if not self.palette:
            return
        palette = np.array(self.palette, dtype=np.float32)
        for i in range(self.count):
            x = int(_halton(self.halton_seed + i + 1, 2) * W)
            y = int(_halton(self.halton_seed + i + 1, 3) * H)
            size = int(rng.integers(self.size_range[0], self.size_range[1] + 1))
            stamp = self._make_stamp(size, rng)
            # Random rotation by transposing / flipping cheaply.
            rot = int(rng.integers(0, 4))
            stamp = np.rot90(stamp, rot)
            colour = palette[int(rng.integers(0, len(palette)))]
            y0, y1 = max(0, y - size // 2), min(H, y - size // 2 + size)
            x0, x1 = max(0, x - size // 2), min(W, x - size // 2 + size)
            sy0 = y0 - (y - size // 2)
            sx0 = x0 - (x - size // 2)
            sy1 = sy0 + (y1 - y0)
            sx1 = sx0 + (x1 - x0)
            patch_mask = stamp[sy0:sy1, sx0:sx1] * self.opacity
            layer_rgb = np.broadcast_to(colour, (y1 - y0, x1 - x0, 3))
            sub = rgba[y0:y1, x0:x1]
            base = sub[..., :3].astype(np.float32)
            a = patch_mask[..., None]
            sub[..., :3] = np.clip(base * (1 - a) + layer_rgb * a, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# HoodBand -- Mustang-style power stripe across the DECK + NOSE panels.
# ---------------------------------------------------------------------------

# DECK and NOSE bboxes from assets/uv_atlas/panel_atlas.json.  Hard-coded so
# the motif is self-contained.  Each entry is (y_lo, y_hi, x_lo, x_hi) in
# canvas pixels.
_HOODBAND_REGIONS = [
    (640,  1520,    4, 1444),   # DECK -- engine cover spine, the big stripe
    (1600, 2048,   80,  984),   # NOSE -- front cone, the continuation
]


@dataclass
class HoodBand(Motif):
    """Paint a feathered horizontal colour band across the DECK and NOSE
    panels -- the canonical Mustang / Cobra fore-aft power stripe.

    The band is centred on the Y-axis midline of each target panel and
    extends across the full X-extent of that panel.  Edges feather out
    with a gaussian falloff so the band reads as a clean racing graphic
    rather than a hard rectangle.

    Parameters
    ----------
    color : (R, G, B)
        Band fill colour.
    opacity : float
        Peak band opacity (0..1) at the centre line.
    half_height : int
        Half-thickness of the solid centre of the band (pixels).  Total
        opaque height is ``2 * half_height``.
    feather : int
        Pixels of gaussian-style soft falloff added beyond the solid
        centre.  Larger values = softer painted edges.
    pinline_color : (R, G, B) | None
        Optional thin contrast line drawn at the top and bottom edge of
        the band -- yacht "boot top" / coachline detail.  ``None`` to
        skip.
    pinline_width : int
        Thickness of each pinline (pixels).
    pinline_offset : int
        Distance from the solid band edge to the pinline centre (pixels).
    regions : sequence of (y_lo, y_hi, x_lo, x_hi) | None
        Panels to paint into.  ``None`` means the default DECK + NOSE.
        Pass a custom list to e.g. paint only on DECK (omit NOSE) or
        only on NOSE -- useful when you want the stripe to live on one
        body section instead of wrapping over the whole top.
    """
    color: Tuple[int, int, int] = (255, 255, 255)
    opacity: float = 0.92
    half_height: int = 70
    feather: int = 24
    pinline_color: Optional[Tuple[int, int, int]] = None
    pinline_width: int = 3
    pinline_offset: int = 14
    regions: Optional[Sequence[Tuple[int, int, int, int]]] = None
    name: str = "HoodBand"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        color = np.array(self.color, dtype=np.float32)
        regions = list(self.regions) if self.regions is not None else _HOODBAND_REGIONS
        for y_lo, y_hi, x_lo, x_hi in regions:
            cy = (y_lo + y_hi) // 2
            yy = np.arange(H, dtype=np.float32)
            dist = np.abs(yy - cy)
            # Plateau inside +/- half_height, gaussian falloff beyond.
            inside = (dist <= self.half_height).astype(np.float32)
            outside = np.where(
                dist > self.half_height,
                np.exp(-((dist - self.half_height) ** 2)
                       / max(1.0, 2.0 * self.feather ** 2)),
                0.0,
            )
            falloff = np.clip(inside + outside, 0.0, 1.0).astype(np.float32)
            # Restrict to panel bbox.
            row_mask = np.zeros(H, dtype=np.float32)
            row_mask[y_lo:y_hi] = 1.0
            falloff = falloff * row_mask
            col_mask = np.zeros(W, dtype=np.float32)
            col_mask[x_lo:x_hi] = 1.0
            alpha = (falloff[:, None] * col_mask[None, :]) * self.opacity
            a = alpha[..., None]
            base = rgba[..., :3].astype(np.float32)
            rgba[..., :3] = np.clip(base * (1 - a) + color[None, None, :] * a,
                                    0, 255).astype(np.uint8)

            if self.pinline_color is not None:
                pin = np.array(self.pinline_color, dtype=np.float32)
                for sign in (-1, +1):
                    py_centre = cy + sign * (self.half_height + self.pinline_offset)
                    py_dist = np.abs(yy - py_centre)
                    pin_mask = np.clip(
                        1.0 - py_dist / max(1.0, self.pinline_width), 0.0, 1.0
                    ).astype(np.float32) ** 1.4
                    pin_mask = pin_mask * row_mask
                    pin_alpha = (pin_mask[:, None] * col_mask[None, :]) * min(
                        1.0, self.opacity + 0.05
                    )
                    pa = pin_alpha[..., None]
                    base = rgba[..., :3].astype(np.float32)
                    rgba[..., :3] = np.clip(
                        base * (1 - pa) + pin[None, None, :] * pa, 0, 255
                    ).astype(np.uint8)


# ---------------------------------------------------------------------------
# CockpitCollar -- thin horizontal coachline at the cockpit-area Y.
# ---------------------------------------------------------------------------

# Restrict the coachline to the canvas X-ranges of the DECK and HERO_FLANK
# panels (engine cover spine + main flank).  Painting outside these ranges
# would land on HIDDEN UV islands or the NOSE_DETAILS strip and waste pixels.
_COCKPIT_COLLAR_X_RANGES = [
    (4,    1444),     # DECK x-extent
    (1032, 2048),     # HERO_FLANK x-extent
]


@dataclass
class CockpitCollar(Motif):
    """Thin horizontal coachline at the cockpit-area Y row.

    Paints a single soft pinline at ``y_pos`` (defaults to 720, which is
    where the InkstonePeony bloom is centred -- empirically the cockpit
    area).  The line is restricted to the X-ranges of the DECK and
    HERO_FLANK panels so it doesn't bleed into HIDDEN UV islands.

    Parameters
    ----------
    color : (R, G, B)
        Coachline colour.
    y_pos : int
        Canvas Y at which the line is drawn.
    line_width : float
        Half-thickness of the line in pixels (3-4 reads as fine pinline,
        6-8 reads as a stronger belt-line).
    opacity : float
        Peak line opacity at the centre.
    """
    color: Tuple[int, int, int] = (220, 180, 95)
    y_pos: int = 720
    line_width: float = 3.5
    opacity: float = 0.95
    name: str = "CockpitCollar"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        c = np.array(self.color, dtype=np.float32)
        yy = np.arange(H, dtype=np.float32)
        dy = np.abs(yy - float(self.y_pos))
        line = np.clip(1.0 - dy / max(1.0, self.line_width), 0.0, 1.0) ** 1.4
        col_mask = np.zeros(W, dtype=np.float32)
        for x_lo, x_hi in _COCKPIT_COLLAR_X_RANGES:
            col_mask[x_lo:x_hi] = 1.0
        alpha = (line[:, None] * col_mask[None, :]) * self.opacity
        a = alpha[..., None]
        base = rgba[..., :3].astype(np.float32)
        rgba[..., :3] = np.clip(base * (1 - a) + c[None, None, :] * a,
                                0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# FenderPinline -- vertical coachlines along the FENDERS panel edges.
# ---------------------------------------------------------------------------

# FENDERS bbox from panel_atlas.json -- (y_lo, y_hi, x_lo, x_hi).
_FENDERS_BBOX = (320, 1840, 780, 996)


@dataclass
class FenderPinline(Motif):
    """Two vertical coachlines tracing the FENDERS panel inner and outer edges.

    The FENDERS panel maps the wheel-arch tops (mirror pair).  Drawing
    thin vertical pinlines at its bbox X-edges places a coachline along
    each fender's UV-island boundary, which corresponds to an edge of
    the fender in 3D.

    Parameters
    ----------
    color : (R, G, B)
        Pinline colour.
    line_width : float
        Half-thickness of each pinline.
    opacity : float
        Peak line opacity.
    """
    color: Tuple[int, int, int] = (245, 220, 150)
    line_width: float = 3.5
    opacity: float = 0.92
    name: str = "FenderPinline"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        c = np.array(self.color, dtype=np.float32)
        y_lo, y_hi, x_lo, x_hi = _FENDERS_BBOX
        row_mask = np.zeros(H, dtype=np.float32)
        row_mask[y_lo:y_hi] = 1.0
        xx = np.arange(W, dtype=np.float32)
        for x_target in (x_lo, x_hi):
            dx = np.abs(xx - float(x_target))
            line = np.clip(1.0 - dx / max(1.0, self.line_width), 0.0, 1.0) ** 1.4
            alpha = (row_mask[:, None] * line[None, :]) * self.opacity
            a = alpha[..., None]
            base = rgba[..., :3].astype(np.float32)
            rgba[..., :3] = np.clip(base * (1 - a) + c[None, None, :] * a,
                                    0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Patina -- subtle FBM luminance modulation for hand-rubbed / aged finish.
# ---------------------------------------------------------------------------


@dataclass
class Vignette(Motif):
    """Multiplicative luminance modulator -- darkens or lightens regions of
    the canvas without overwriting hue.

    Modes
    -----
    "radial"
        Corner darkening (classic photographic vignette).  Strength
        negative = darkens corners, positive = lightens them.
    "top" / "bottom" / "left" / "right"
        Linear band falloff anchored to the named edge.  At the edge,
        ``strength`` is applied at full force; ``falloff`` controls how
        far into the canvas the modulation extends.

    Parameters
    ----------
    mode : str
        "radial" | "top" | "bottom" | "left" | "right".
    strength : float
        Modulation amplitude.  -1 = full black at the affected zone,
        +1 = full white.  Typical -0.25 .. -0.40 for subtle darkening,
        +0.15 .. +0.30 for subtle lightening.
    falloff : float
        Distance from the anchor (0..1 of canvas dimension) over which
        the modulation fades to zero.
    """
    mode: str = "radial"
    strength: float = -0.30
    falloff: float = 0.7
    name: str = "Vignette"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        if self.mode == "radial":
            yy = (np.arange(H, dtype=np.float32) - H / 2.0) / (H / 2.0)
            xx = (np.arange(W, dtype=np.float32) - W / 2.0) / (W / 2.0)
            r = np.sqrt(yy[:, None] ** 2 + xx[None, :] ** 2)
            weight = np.clip(r / max(self.falloff, 1e-3), 0.0, 1.0)
        elif self.mode == "top":
            yy = np.arange(H, dtype=np.float32) / max(1, H - 1)
            w = np.clip((self.falloff - yy) / max(self.falloff, 1e-3), 0.0, 1.0)
            weight = np.broadcast_to(w[:, None], (H, W))
        elif self.mode == "bottom":
            yy = np.arange(H, dtype=np.float32) / max(1, H - 1)
            w = np.clip((yy - (1.0 - self.falloff)) / max(self.falloff, 1e-3),
                        0.0, 1.0)
            weight = np.broadcast_to(w[:, None], (H, W))
        elif self.mode == "left":
            xx = np.arange(W, dtype=np.float32) / max(1, W - 1)
            w = np.clip((self.falloff - xx) / max(self.falloff, 1e-3), 0.0, 1.0)
            weight = np.broadcast_to(w[None, :], (H, W))
        elif self.mode == "right":
            xx = np.arange(W, dtype=np.float32) / max(1, W - 1)
            w = np.clip((xx - (1.0 - self.falloff)) / max(self.falloff, 1e-3),
                        0.0, 1.0)
            weight = np.broadcast_to(w[None, :], (H, W))
        else:
            return
        mod = 1.0 + float(self.strength) * weight
        base = rgba[..., :3].astype(np.float32)
        rgba[..., :3] = np.clip(base * mod[..., None], 0, 255).astype(np.uint8)


@dataclass
class Patina(Motif):
    """Whole-body multiplicative noise overlay -- the "hand-polished" pass.

    Generates multi-octave FBM noise and multiplies the canvas RGB by
    ``1 + (noise - 0.5) * 2 * strength`` so the average luminance is
    preserved while introducing fine surface variation.  At
    ``strength=0.12-0.18`` the effect is barely visible at distance but
    reads as a real, aged, hand-rubbed surface up close -- removing the
    "CGI-perfect" feel from procedural wood / lacquer skins.

    Parameters
    ----------
    strength : float
        Modulation amplitude.  0.10 = whisper, 0.25 = visible texture.
    octaves : int
        FBM octaves -- more octaves = finer micro-grain.
    """
    strength: float = 0.15
    octaves: int = 4
    name: str = "Patina"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        noise = _fbm(rng, (H, W), octaves=int(self.octaves))
        mod = 1.0 + (noise.astype(np.float32) - 0.5) * 2.0 * float(self.strength)
        base = rgba[..., :3].astype(np.float32)
        rgba[..., :3] = np.clip(base * mod[..., None], 0, 255).astype(np.uint8)
