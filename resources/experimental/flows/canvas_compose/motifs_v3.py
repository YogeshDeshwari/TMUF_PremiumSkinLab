"""Motifs v3 -- new building blocks for the 9 outside-the-box skins.

These are kept separate from motifs.py to avoid bloating the main file.
Each motif obeys the same `paint(rgba, rng)` protocol.

Contents:
    InkStrokes      : procedural pen-stroke text / handwriting
    MicroStamp      : hex-grid micro-pattern stamps (Edo komon)
    HyperbolicShock : Edgerton-style schlieren bow shock
    ScanlineCRT     : VHS chromatic split + scan lines + dropout bars
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .composer import Motif


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _composite_rgb_alpha(rgba: np.ndarray, rgb_layer: np.ndarray,
                         alpha: np.ndarray) -> None:
    """In-place over-blend: `rgba.rgb = rgba.rgb*(1-a) + rgb_layer*a`."""
    a = np.clip(alpha, 0.0, 1.0)[..., None]
    base = rgba[..., :3].astype(np.float32)
    rgba[..., :3] = np.clip(base * (1.0 - a) + rgb_layer * a, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# InkStrokes
# ---------------------------------------------------------------------------


@dataclass
class InkStrokes(Motif):
    """Procedural ink-pen strokes: equations, handwriting, glyph art.

    A stroke is a polyline (list of (x, y) waypoints) drawn with a
    rounded brush of `thickness` pixels and slight pressure variation.
    The motif owns no glyph corpus -- callers pass strokes in directly
    so we can build whiteboard equations, polaroid captions, schlieren
    annotations, etc. with the same renderer.

    Caller-supplied data
    --------------------
    strokes : list of polylines (each a list of (x, y) tuples)
        Coordinates in canvas pixel space.  Each polyline is one
        connected stroke (lifting the pen ends a polyline).
    color : (R, G, B)
        Ink colour.
    thickness : float
        Nominal stroke width in pixels (slight per-segment jitter
        applied internally for hand-drawn feel).
    pressure_jitter : float
        Width modulation amplitude, 0..1.  Realistic felt-pen ~0.25.
    end_taper : float
        How much each stroke tapers off at the end (0 = no taper).
    smoothness : int
        Bezier interpolation samples per segment (higher = smoother).
    opacity : float
        Layer opacity.  Real ink is near-opaque, so 0.95 is typical.
    """
    strokes: Sequence[Sequence[Tuple[float, float]]] = field(default_factory=list)
    color: Tuple[int, int, int] = (24, 24, 28)
    thickness: float = 6.0
    pressure_jitter: float = 0.25
    end_taper: float = 0.20
    smoothness: int = 8
    opacity: float = 0.95
    name: str = "InkStrokes"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        if not self.strokes:
            return
        # Build an L-mask using PIL's anti-aliased line + ellipse caps,
        # then composite at self.color.
        mask = Image.new("L", (W, H), 0)
        draw = ImageDraw.Draw(mask)
        for poly in self.strokes:
            if len(poly) < 2:
                continue
            pts = [(float(p[0]), float(p[1])) for p in poly]
            n = len(pts)
            for i in range(n - 1):
                x0, y0 = pts[i]
                x1, y1 = pts[i + 1]
                # Pressure modulation: thinner at start, fatter mid, taper end.
                t = i / max(n - 1, 1)
                taper = 1.0 - self.end_taper * (t ** 2)
                jit = 1.0 + (rng.random() - 0.5) * self.pressure_jitter
                w = max(1.0, self.thickness * taper * jit)
                # Round cap implemented as ellipse at each endpoint.
                r = w / 2.0
                draw.ellipse([x0 - r, y0 - r, x0 + r, y0 + r], fill=255)
                draw.line([(x0, y0), (x1, y1)], fill=255, width=int(round(w)))
            # Final cap.
            xe, ye = pts[-1]
            r = self.thickness * 0.5
            draw.ellipse([xe - r, ye - r, xe + r, ye + r], fill=255)
        mask_arr = np.array(mask, dtype=np.float32) / 255.0
        # Slight blur for anti-alias smoothness on hi-res canvas.
        mask_arr = np.array(Image.fromarray((mask_arr * 255).astype(np.uint8))
                            .filter(ImageFilter.GaussianBlur(radius=0.7))) / 255.0
        col = np.array(self.color, dtype=np.float32)
        rgb_layer = np.broadcast_to(col, (H, W, 3))
        _composite_rgb_alpha(rgba, rgb_layer, mask_arr * self.opacity)


# ---------------------------------------------------------------------------
# MicroStamp -- Edo komon hex-grid micro pattern
# ---------------------------------------------------------------------------


@dataclass
class MicroStamp(Motif):
    """Tile a small 'stamp' (16-32 px) across the canvas on a hex/square grid.

    Used for Edo komon kimono micro-patterns: at race speed the eye
    averages the stamps into a solid colour; up close the geometric
    motif is legible.  Three named stamps are built in:

      * "kikko"   -- nested hexagons (turtle shell)
      * "asanoha" -- six-pointed hemp-leaf star
      * "shippo"  -- four overlapping circles (Buddhist treasures)

    Several stamps may be requested simultaneously; each cell of the
    grid picks one at random with probabilities supplied by
    `stamp_weights` (defaults to uniform).

    Parameters
    ----------
    stamps : list[str]
        Names from the built-in atlas.
    cell_px : int
        Side length of each stamp in canvas pixels (also the grid
        spacing).  6-12 px gives the classic scale-switch read.
    stamp_weights : list[float] or None
        Relative probability of each stamp; same length as `stamps`.
    color : (R, G, B)
        Stamp ink colour.
    background : (R, G, B) or None
        If given, fills every cell with this colour first (typically
        the burgundy field).  None = paint stamps without overwriting
        the canvas background.
    opacity : float
        Stamp layer opacity (the ink, not the background).
    grid : str
        "square" or "hex".  Hex shifts every other row by half a cell.
    """
    stamps: Sequence[str] = field(default_factory=lambda: ["kikko"])
    cell_px: int = 24
    stamp_weights: Optional[Sequence[float]] = None
    color: Tuple[int, int, int] = (230, 215, 180)
    background: Optional[Tuple[int, int, int]] = None
    opacity: float = 0.55
    grid: str = "hex"
    name: str = "MicroStamp"

    @staticmethod
    def _kikko(c: int) -> np.ndarray:
        # Nested hexagons.
        s = c
        img = Image.new("L", (s, s), 0)
        draw = ImageDraw.Draw(img)
        cx, cy = s / 2, s / 2
        for r_frac, w in ((0.45, 1), (0.28, 1)):
            r = r_frac * s / 2
            pts = []
            for i in range(6):
                ang = math.pi / 6 + i * math.pi / 3
                pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
            draw.polygon(pts, outline=255, width=max(1, w))
        return np.array(img, dtype=np.float32) / 255.0

    @staticmethod
    def _asanoha(c: int) -> np.ndarray:
        # Six-petaled star: hexagon with 3 long diagonals.
        s = c
        img = Image.new("L", (s, s), 0)
        draw = ImageDraw.Draw(img)
        cx, cy = s / 2, s / 2
        r = 0.45 * s / 2
        pts = []
        for i in range(6):
            ang = math.pi / 6 + i * math.pi / 3
            pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
        draw.polygon(pts, outline=255, width=1)
        # Three diagonals through the centre to alternating vertices.
        for i in range(3):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 3]
            draw.line([(x1, y1), (x2, y2)], fill=255, width=1)
        # Spokes from centre to each vertex.
        for x, y in pts:
            draw.line([(cx, cy), (x, y)], fill=255, width=1)
        return np.array(img, dtype=np.float32) / 255.0

    @staticmethod
    def _shippo(c: int) -> np.ndarray:
        # Four overlapping circles (Buddhist treasures motif).
        s = c
        img = Image.new("L", (s, s), 0)
        draw = ImageDraw.Draw(img)
        r = 0.42 * s / 2
        cx, cy = s / 2, s / 2
        for dx, dy in [(-r * 0.7, 0), (r * 0.7, 0), (0, -r * 0.7), (0, r * 0.7)]:
            draw.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r],
                         outline=255, width=1)
        return np.array(img, dtype=np.float32) / 255.0

    def _make_atlas(self) -> List[np.ndarray]:
        atlas = []
        for name in self.stamps:
            if name == "kikko":
                atlas.append(self._kikko(self.cell_px))
            elif name == "asanoha":
                atlas.append(self._asanoha(self.cell_px))
            elif name == "shippo":
                atlas.append(self._shippo(self.cell_px))
            else:
                raise ValueError(f"Unknown stamp name: {name}")
        return atlas

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        atlas = self._make_atlas()
        if not atlas:
            return
        c = self.cell_px
        weights = (np.array(self.stamp_weights, dtype=np.float64)
                   if self.stamp_weights is not None
                   else np.ones(len(atlas)))
        weights = weights / weights.sum()

        # Optional solid background fill.
        if self.background is not None:
            rgba[..., 0] = self.background[0]
            rgba[..., 1] = self.background[1]
            rgba[..., 2] = self.background[2]

        # Build one big mask by tiling stamps.
        big = np.zeros((H, W), dtype=np.float32)
        rows = math.ceil(H / c) + 1
        cols = math.ceil(W / c) + 1
        for ry in range(rows):
            offset = (c // 2) if (self.grid == "hex" and ry % 2 == 1) else 0
            y0 = ry * c
            if y0 >= H:
                continue
            for cx in range(cols):
                x0 = cx * c - offset
                if x0 + c < 0 or x0 >= W:
                    continue
                idx = int(rng.choice(len(atlas), p=weights))
                stamp = atlas[idx]
                # Cropped placement -- handles edges.
                sx0 = max(0, -x0)
                sy0 = max(0, -y0)
                tx0 = max(0, x0)
                ty0 = max(0, y0)
                tx1 = min(W, x0 + c)
                ty1 = min(H, y0 + c)
                sx1 = sx0 + (tx1 - tx0)
                sy1 = sy0 + (ty1 - ty0)
                if tx1 > tx0 and ty1 > ty0:
                    big[ty0:ty1, tx0:tx1] = np.maximum(
                        big[ty0:ty1, tx0:tx1], stamp[sy0:sy1, sx0:sx1])
        col = np.array(self.color, dtype=np.float32)
        rgb_layer = np.broadcast_to(col, (H, W, 3))
        _composite_rgb_alpha(rgba, rgb_layer, big * self.opacity)


# ---------------------------------------------------------------------------
# HyperbolicShock -- Edgerton schlieren bow shock + Mach cone
# ---------------------------------------------------------------------------


@dataclass
class HyperbolicShock(Motif):
    """Render an Edgerton-style supersonic shock pattern in B/W.

    Geometry: bow shock at the bullet nose obeys the conic equation

        x = a + sqrt(1 + (y/b)^2) * scale

    rotated and translated so the apex sits at `apex` with the cone
    opening toward +x.  Mach angle theta = arcsin(1/M); for M=2 this
    is ~30 degrees.  The wake aft of the bullet is rendered as several
    softer parallel streaks.

    Parameters
    ----------
    apex : (x, y)
        Bullet nose position in canvas px.
    direction_deg : float
        Angle (degrees) the bullet is pointing; 0 = +x axis.
    mach : float
        Mach number; sets cone opening.  Real bullet ~2.0.
    bullet_length : int
    bullet_radius : int
    shock_width : int
        Pixel thickness of the bow-shock contour line.
    shock_color : (R, G, B)
    bg_color : (R, G, B)
    show_wake : bool
    wake_streaks : int
    """
    apex: Tuple[int, int] = (1024, 1024)
    direction_deg: float = 180.0  # pointing +x by default
    mach: float = 2.0
    bullet_length: int = 240
    bullet_radius: int = 50
    shock_width: int = 9
    shock_color: Tuple[int, int, int] = (28, 30, 36)
    bg_color: Optional[Tuple[int, int, int]] = (192, 196, 202)
    show_wake: bool = True
    wake_streaks: int = 9
    name: str = "HyperbolicShock"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        if self.bg_color is not None:
            rgba[..., 0] = self.bg_color[0]
            rgba[..., 1] = self.bg_color[1]
            rgba[..., 2] = self.bg_color[2]

        ax, ay = self.apex
        theta = math.radians(self.direction_deg)
        ct = math.cos(theta)
        st = math.sin(theta)

        # Build shock-line pixel coordinates in BULLET frame: x along
        # bullet axis, y perpendicular.  Bow shock: classic hyperbola.
        # mach_angle:
        mu = math.asin(min(1.0, 1.0 / max(self.mach, 1.001)))
        b = self.bullet_radius * 1.2
        a = self.bullet_length * 0.18
        # Trace from y = -large..+large.
        Y = np.linspace(-1500, 1500, 4000, dtype=np.float32)
        # Hyperbola: x = a * sqrt(1 + (y/b)^2).  Then shift apex.
        Xh = a * np.sqrt(1.0 + (Y / b) ** 2)
        # Asymptote angle is arctan(b/a).  We want it to match Mach mu,
        # so rescale: tan(mu) = b/a -> a = b / tan(mu).
        a_target = b / math.tan(mu)
        Xh = a_target * np.sqrt(1.0 + (Y / b) ** 2)
        # Origin at apex (Xh starts at a_target which is the nose offset
        # along bullet axis where the shock is born).  Offset back so
        # the curve passes through (0,0) -> subtract a_target.
        Xh -= a_target

        # Map to world frame: apply rotation + translation.
        Xw = ax + Xh * ct - Y * st
        Yw = ay + Xh * st + Y * ct

        # Rasterise via Pillow for crisp anti-aliased line.
        line_img = Image.new("L", (W, H), 0)
        draw = ImageDraw.Draw(line_img)
        pts = list(zip(Xw.tolist(), Yw.tolist()))
        # Filter to in-bounds-ish.
        in_pts = [(x, y) for x, y in pts
                  if -50 < x < W + 50 and -50 < y < H + 50]
        if len(in_pts) >= 2:
            draw.line(in_pts, fill=255, width=self.shock_width, joint="curve")

        # Bullet body: ellipse along axis.
        bl = self.bullet_length
        br = self.bullet_radius
        # Bullet centre is BEHIND the apex (in -x bullet direction).
        bx = ax - (bl * 0.5) * ct
        by = ay - (bl * 0.5) * st
        # Approximate bullet as rotated ellipse via polygon with N points.
        ell_pts = []
        for k in range(64):
            t = k / 64.0 * 2 * math.pi
            ex = (bl / 2) * math.cos(t)
            ey = br * math.sin(t)
            wx = bx + ex * ct - ey * st
            wy = by + ex * st + ey * ct
            ell_pts.append((wx, wy))
        draw.polygon(ell_pts, fill=255)

        # Wake streaks aft of bullet: short parallel hyperbola-like rays.
        if self.show_wake:
            for k in range(self.wake_streaks):
                u = (k + 1) / (self.wake_streaks + 1) - 0.5  # -0.5..0.5
                yo = u * br * 1.4
                # Streak in bullet -x direction with slight scatter.
                sx0 = bx - (bl * 0.55) * ct - yo * st
                sy0 = by - (bl * 0.55) * st + yo * ct
                length = bl * (2.5 + rng.random() * 1.5)
                jitter = (rng.random() - 0.5) * 0.2
                sx1 = sx0 - length * (ct + jitter * st)
                sy1 = sy0 - length * (st - jitter * ct)
                draw.line([(sx0, sy0), (sx1, sy1)],
                          fill=140, width=max(2, self.shock_width // 2))

        mask = np.array(line_img, dtype=np.float32) / 255.0
        # Slight Gaussian softening of mask edges -- real schlieren are not razor-sharp.
        mask = np.array(Image.fromarray((mask * 255).astype(np.uint8))
                        .filter(ImageFilter.GaussianBlur(radius=1.4))) / 255.0
        col = np.array(self.shock_color, dtype=np.float32)
        rgb_layer = np.broadcast_to(col, (H, W, 3))
        _composite_rgb_alpha(rgba, rgb_layer, mask)


# ---------------------------------------------------------------------------
# ScanlineCRT -- VHS chromatic split + scan lines + dropouts
# ---------------------------------------------------------------------------


@dataclass
class ScanlineCRT(Motif):
    """Apply VHS / CRT corruption to the *existing* canvas content.

    This is a POST-PROCESS motif: paint your source image first, then
    apply ScanlineCRT to corrupt it.  The corruptions are:

    * **Chromatic aberration** -- horizontally shift the R, G, B
      channels apart (R left, B right) by `chroma_shift_px` pixels.
    * **Scan lines** -- subtract a darker stripe every `scanline_period`
      rows, simulating CRT line gap.
    * **Vertical hold drift** -- a slight sinusoidal y-offset across
      x, simulating an unstable signal lock.
    * **Dropout bars** -- a few horizontal bands of solid noise or
      black, simulating tape damage / magnetic dropout.

    Parameters
    ----------
    chroma_shift_px : int
    scanline_period : int
    scanline_strength : float
    drift_amp_px : float
    drift_periods : float
    n_dropouts : int
    dropout_height_px : Tuple[int, int]
    """
    chroma_shift_px: int = 8
    scanline_period: int = 4
    scanline_strength: float = 0.32
    drift_amp_px: float = 4.0
    drift_periods: float = 0.7
    n_dropouts: int = 6
    dropout_height_px: Tuple[int, int] = (3, 14)
    name: str = "ScanlineCRT"

    def paint(self, rgba: np.ndarray, rng: np.random.Generator) -> None:
        H, W, _ = rgba.shape
        rgb = rgba[..., :3].astype(np.float32)

        if self.chroma_shift_px > 0:
            shifted = np.zeros_like(rgb)
            s = self.chroma_shift_px
            shifted[:, :-s, 0] = rgb[:, s:, 0]            # R shifts left
            shifted[:, s:, 0]  = rgb[:, s:, 0]
            shifted[:, :, 0]   = np.roll(rgb[:, :, 0], -s, axis=1)
            shifted[:, :, 1]   = rgb[:, :, 1]              # G stays
            shifted[:, :, 2]   = np.roll(rgb[:, :, 2], +s, axis=1)
            rgb = shifted

        # Vertical hold drift -- small sinusoidal y-shift modulated by x.
        if self.drift_amp_px > 0:
            xs = np.arange(W, dtype=np.float32)
            dy = self.drift_amp_px * np.sin(
                2 * np.pi * self.drift_periods * xs / W)
            ys = np.arange(H, dtype=np.float32)[:, None]
            ys_shift = ys + dy[None, :]
            ys_shift = np.clip(ys_shift, 0, H - 1)
            yi = ys_shift.astype(np.int32)
            xi = np.broadcast_to(np.arange(W, dtype=np.int32)[None, :], (H, W))
            rgb = rgb[yi, xi]

        # Scan lines -- multiplicative every scanline_period rows.
        if self.scanline_period >= 2 and self.scanline_strength > 0:
            mod = np.ones(H, dtype=np.float32)
            mod[::self.scanline_period] = 1.0 - self.scanline_strength
            rgb *= mod[:, None, None]

        # Dropout bars -- horizontal bars of black or tape-noise colour.
        for _ in range(self.n_dropouts):
            h = int(rng.integers(self.dropout_height_px[0],
                                 self.dropout_height_px[1] + 1))
            y0 = int(rng.integers(0, H - h))
            kind = rng.random()
            if kind < 0.6:
                rgb[y0:y0 + h, :, :] = 0
            else:
                # Cyan-magenta-yellow tape glitch line.
                tape = np.array([
                    (240, 200, 60), (220, 60, 200), (60, 220, 200),
                ], dtype=np.float32)
                idx = int(rng.integers(0, 3))
                rgb[y0:y0 + h, :, :] = tape[idx][None, None, :]

        rgba[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
