from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, gaussian_filter

from src.dds.tmnf_dds import build_dds_dxt5_bytes
from src.stock_diffuse.calibration import SIZE, hx, load_fields, mudguard_ids, project_view
from src.stock_diffuse.package import write_stable_zip_entry


ROOT = Path(__file__).resolve().parents[2]
REF_DIR = ROOT / "resources" / "authoritative" / "reference"
CANDIDATE_NAMES = [
    "black_magenta_cyan_blade",
    "black_cyan_spine",
    "violet_cyber_flow",
    "dark_neon_louver",
    "magenta_cyan_race_proto",
]


@dataclass(frozen=True)
class Candidate:
    name: str
    base: str
    base2: str
    primary: str
    secondary: str
    highlight: str
    spine_width: float
    blade_slope: float
    blade_offset: float
    rear_louver_count: float
    mudguard_mode: str


CANDIDATES = [
    Candidate(
        "black_magenta_cyan_blade",
        "#050507",
        "#161820",
        "#ff00b8",
        "#00d8ff",
        "#f6f2ff",
        0.050,
        0.42,
        0.16,
        16.0,
        "primary_front",
    ),
    Candidate(
        "black_cyan_spine",
        "#040608",
        "#111a1f",
        "#00d8ff",
        "#ff25c8",
        "#edf8ff",
        0.064,
        0.35,
        0.21,
        18.0,
        "secondary_front",
    ),
    Candidate(
        "violet_cyber_flow",
        "#07050b",
        "#17101d",
        "#d600ff",
        "#00e0ff",
        "#fff5ff",
        0.044,
        0.50,
        0.13,
        14.0,
        "split",
    ),
    Candidate(
        "dark_neon_louver",
        "#050607",
        "#17191d",
        "#ff149a",
        "#00cfff",
        "#f7fbff",
        0.038,
        0.30,
        0.24,
        22.0,
        "secondary_front",
    ),
    Candidate(
        "magenta_cyan_race_proto",
        "#060506",
        "#1b151d",
        "#ff0090",
        "#00f0ff",
        "#fff8fb",
        0.056,
        0.46,
        0.18,
        17.0,
        "primary_front",
    ),
]


def _axis_fields(fields: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    pos = fields["pos"]
    axes = fields["axes"]
    length = pos[..., axes["LEN"]]
    lateral = pos[..., axes["LAT"]]
    height = pos[..., axes["HGT"]]
    symmetry = np.abs(lateral - 0.5)
    return length, lateral, height, symmetry


def _soft(mask: np.ndarray, sigma: float = 1.2) -> np.ndarray:
    return np.clip(gaussian_filter(mask.astype(np.float32), sigma=sigma), 0.0, 1.0)


def _blend(rgb: np.ndarray, mask: np.ndarray, color: str, strength: float = 1.0) -> None:
    amount = _soft(mask) * strength
    if amount.max() <= 0:
        return
    rgb[:] = rgb * (1.0 - amount[..., None]) + hx(color) * amount[..., None]


def _thin_line(field: np.ndarray, center: np.ndarray | float, width: float) -> np.ndarray:
    return np.abs(field - center) < width


def _build_masks(fields: dict[str, Any], candidate: Candidate) -> dict[str, np.ndarray]:
    coverage = fields["coverage"]
    labels = fields["labels"]
    length, lateral, height, symmetry = _axis_fields(fields)

    body = coverage & (labels > 0)
    upper = body & (height > 0.48)
    lower = body & (height <= 0.48)
    nose = body & (length > 0.72)
    rear = body & (length < 0.36)
    deck = upper & (height > 0.58)
    engine_deck = rear & deck
    side_band = lower & (height > 0.22) & (symmetry > 0.18) & (symmetry < 0.43)
    mudguards = np.isin(labels, mudguard_ids(fields["zones"]))

    spine_width = candidate.spine_width + 0.018 * np.clip(length - 0.68, 0, 1)
    center_spine = upper & _thin_line(symmetry, 0.0, spine_width)
    nose_spear = nose & _thin_line(symmetry, 0.0, candidate.spine_width * (1.35 - 0.45 * (length - 0.72)))

    blade_center = candidate.blade_offset + candidate.blade_slope * np.clip(length - 0.28, -0.12, 0.52)
    side_blade = side_band & _thin_line(symmetry, blade_center, 0.032)
    secondary_blade = side_band & _thin_line(symmetry, np.clip(blade_center + 0.075, 0.18, 0.46), 0.020)

    rear_louver_phase = ((1.0 - length) * candidate.rear_louver_count + symmetry * 2.6) % 1.0
    rear_louvers = engine_deck & (symmetry > 0.08) & (symmetry < 0.35) & (rear_louver_phase < 0.30)
    rear_center_glow = engine_deck & _thin_line(symmetry, 0.0, max(candidate.spine_width * 0.72, 0.030))

    shoulder_line = upper & (symmetry > 0.20) & (symmetry < 0.33) & _thin_line(
        height, 0.62 + 0.18 * (length - 0.45), 0.026
    )
    tail_bar = rear & _thin_line(length, 0.12, 0.022) & (height > 0.30)
    mudguard_edge = mudguards & (
        (symmetry > 0.31)
        | (height > 0.62)
        | (length > 0.76)
        | (length < 0.20)
    )

    return {
        "body": body,
        "mudguards": mudguards,
        "center_spine": center_spine,
        "nose_spear": nose_spear,
        "side_blade": side_blade,
        "secondary_blade": secondary_blade,
        "rear_louvers": rear_louvers,
        "rear_center_glow": rear_center_glow,
        "shoulder_line": shoulder_line,
        "tail_bar": tail_bar,
        "mudguard_edge": mudguard_edge,
    }


def build_premium_rgba(candidate: Candidate) -> tuple[Image.Image, dict[str, float]]:
    fields = load_fields()
    coverage = fields["coverage"]
    labels = fields["labels"]
    length, _lateral, height, symmetry = _axis_fields(fields)
    masks = _build_masks(fields, candidate)

    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    alpha = np.full((SIZE, SIZE), 112, dtype=np.float32)

    depth = 0.62 + 0.18 * length + 0.12 * height - 0.10 * np.clip(symmetry / 0.5, 0, 1)
    rgb[coverage] = hx(candidate.base)
    rgb[coverage] = rgb[coverage] * (1.0 - depth[coverage, None]) + hx(candidate.base2) * depth[coverage, None]

    _blend(rgb, masks["center_spine"], candidate.primary, 0.95)
    _blend(rgb, masks["nose_spear"], candidate.primary, 1.00)
    _blend(rgb, masks["side_blade"], candidate.secondary, 0.92)
    _blend(rgb, masks["secondary_blade"], candidate.primary, 0.72)
    _blend(rgb, masks["rear_louvers"], candidate.secondary, 0.86)
    _blend(rgb, masks["rear_center_glow"], candidate.primary, 0.82)
    _blend(rgb, masks["shoulder_line"], candidate.highlight, 0.62)
    _blend(rgb, masks["tail_bar"], candidate.secondary, 0.95)

    if candidate.mudguard_mode == "split":
        _blend(rgb, masks["mudguards"] & (length > 0.5), candidate.primary, 0.72)
        _blend(rgb, masks["mudguards"] & (length <= 0.5), candidate.secondary, 0.72)
    elif candidate.mudguard_mode == "secondary_front":
        _blend(rgb, masks["mudguards"], candidate.primary, 0.38)
        _blend(rgb, masks["mudguard_edge"] & (length > 0.5), candidate.secondary, 0.88)
        _blend(rgb, masks["mudguard_edge"] & (length <= 0.5), candidate.primary, 0.78)
    else:
        _blend(rgb, masks["mudguards"], candidate.secondary, 0.38)
        _blend(rgb, masks["mudguard_edge"] & (length > 0.5), candidate.primary, 0.88)
        _blend(rgb, masks["mudguard_edge"] & (length <= 0.5), candidate.secondary, 0.78)

    seams = binary_dilation(
        ((labels != np.roll(labels, 1, 0)) | (labels != np.roll(labels, 1, 1))) & (labels > 0),
        iterations=1,
    )
    rgb[seams] *= 0.72

    ao_path = REF_DIR / "official_prelight_AO.png"
    if ao_path.exists():
        ao = np.asarray(Image.open(ao_path).convert("L").resize((SIZE, SIZE)), dtype=np.float32)
        rgb *= (0.76 + 0.24 * ao / 255.0)[..., None]

    accent = (
        masks["center_spine"]
        | masks["nose_spear"]
        | masks["side_blade"]
        | masks["secondary_blade"]
        | masks["rear_louvers"]
        | masks["rear_center_glow"]
        | masks["tail_bar"]
        | masks["mudguard_edge"]
    )
    alpha[accent] = 148
    alpha[masks["shoulder_line"]] = 136

    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    metrics = _style_metrics(out, coverage)
    return Image.fromarray(out, "RGBA"), metrics


def _style_metrics(rgba: np.ndarray, coverage: np.ndarray) -> dict[str, float]:
    rgb = rgba[..., :3].astype(np.float32)
    lum = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    denom = max(int(coverage.sum()), 1)
    magenta = coverage & (rgb[..., 0] > 135) & (rgb[..., 2] > 105) & (rgb[..., 1] < 95)
    cyan = coverage & (rgb[..., 1] > 110) & (rgb[..., 2] > 130) & (rgb[..., 0] < 95)
    dark = coverage & (lum < 80)
    return {
        "dark_pixel_ratio": round(float(dark.sum() / denom), 6),
        "magenta_accent_ratio": round(float(magenta.sum() / denom), 6),
        "cyan_accent_ratio": round(float(cyan.sum() / denom), 6),
    }


def _write_candidate(candidate: Candidate) -> dict[str, str]:
    out_skin = ROOT / "out" / "skins" / f"{candidate.name}.zip"
    out_preview = ROOT / "out" / "previews" / f"{candidate.name}_projected_side_top_rear.png"
    out_atlas = ROOT / "out" / "previews" / f"{candidate.name}_atlas.png"
    out_report = ROOT / "out" / "reports" / f"{candidate.name}.json"
    for path in (out_skin.parent, out_preview.parent, out_report.parent):
        path.mkdir(parents=True, exist_ok=True)

    image, metrics = build_premium_rgba(candidate)
    icon = image.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS).convert("RGBA")

    with zipfile.ZipFile(out_skin, "w", zipfile.ZIP_DEFLATED) as zf:
        write_stable_zip_entry(zf, "Diffuse.dds", build_dds_dxt5_bytes(image, mipmaps=True))
        write_stable_zip_entry(zf, "Icon.dds", build_dds_dxt5_bytes(icon, mipmaps=True))

    image.save(out_atlas)
    fields = load_fields()
    rgba = np.asarray(image)
    side = project_view(rgba, "side", fields)
    top = project_view(rgba, "top", fields)
    rear = project_view(rgba, "rear", fields)
    pad = 14
    canvas = Image.new("RGB", (side.width + rear.width + pad * 3, side.height + top.height + pad * 3), (10, 10, 12))
    canvas.paste(side, (pad, pad))
    canvas.paste(top, (pad, pad * 2 + side.height))
    canvas.paste(rear, (pad * 2 + side.width, pad))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 2), "side", fill=(230, 230, 240))
    draw.text((pad, pad + side.height + 2), "top", fill=(230, 230, 240))
    draw.text((pad * 2 + side.width, 2), "rear", fill=(230, 230, 240))
    canvas.save(out_preview)

    report = {
        "skin_name": candidate.name,
        "route": "stock_diffuse_only",
        "package_files": ["Diffuse.dds", "Icon.dds"],
        "tmuf_smoke_test": "not_run",
        "proof_gate": {
            "calibration_stock_diffuse": "required_before_proven_use",
            "premium_visual_acceptance": "required_after_generation",
        },
        "evidence_status": {
            "stock_diffuse_route": "proven_by_local_docs_and_package_contract",
            "gbuffer_mapping": "experimental_until_tmuf_smoke",
            "psd_parts_masks": "local_authoritative_input",
            "ao_prelight": "local_authoritative_input",
            "donor_gbx": "not_used",
            "details_dds": "not_used",
            "projshad_dds": "not_used",
        },
        "design_rules": [
            "black_charcoal_base",
            "magenta_cyan_accents",
            "broad_gbuffer_aligned_shapes",
            "symmetric_rear_engine_panels",
            "no_vignette",
            "no_random_scatter",
            "no_stadiumcar_v2_uvs",
            "no_ch2026_donor_assumptions",
        ],
        "masks_used": [
            "center_spine",
            "nose_spear",
            "side_blade",
            "secondary_blade",
            "rear_louvers",
            "rear_center_glow",
            "shoulder_line",
            "tail_bar",
            "mudguard_edge",
        ],
        "style_metrics": metrics,
        "known_risks": [
            "GBuffer placement remains experimental until the calibration skin is smoke-tested in TMUF.",
            "Projected previews are local proof aids; they are not a substitute for in-game visual acceptance.",
            "Diffuse alpha is conservative and not a fully tuned gloss/specular map yet.",
        ],
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    return {
        "name": candidate.name,
        "zip": str(out_skin),
        "atlas": str(out_atlas),
        "projection": str(out_preview),
        "report": str(out_report),
    }


def save_batch() -> list[dict[str, str]]:
    return [_write_candidate(candidate) for candidate in CANDIDATES]


def main() -> int:
    outputs = save_batch()
    for item in outputs:
        print(f"wrote {item['zip']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
