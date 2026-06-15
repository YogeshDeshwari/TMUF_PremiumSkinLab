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
from src.evidence.artifact_trace import stock_output_artifacts
from src.evidence.input_trace import PREMIUM_DIFFUSE_INPUTS, input_evidence
from src.evidence.panel_visual_coverage import build_panel_visual_coverage
from src.stock_diffuse.calibration import SIZE, hx, load_fields, project_view
from src.stock_diffuse.package import write_stable_zip_entry
from src.stock_diffuse.panel_masks import PremiumMaskParams, build_stock_panel_masks, mask_report_entries


ROOT = Path(__file__).resolve().parents[2]
REF_DIR = ROOT / "resources" / "authoritative" / "reference"
BATCH_INDEX = ROOT / "out" / "reports" / "premium_batch_index.json"
CANDIDATE_NAMES = [
    "black_magenta_cyan_blade",
    "black_cyan_spine",
    "violet_cyber_flow",
    "dark_neon_louver",
    "magenta_cyan_race_proto",
]
PREMIUM_MASK_NAMES = [
    "center_spine",
    "nose_spear",
    "side_blade",
    "secondary_blade",
    "rear_louvers",
    "rear_center_glow",
    "shoulder_line",
    "tail_bar",
    "mudguards",
    "mudguard_edge",
    "tailwing",
    "side_wings",
    "mirrors",
    "underplate",
    "main_body_under",
]
PANEL_FAMILY_MASK_NAMES = [
    "nose_deck_generated_panels",
    "nose_floor_generated_panels",
    "nose_side_generated_panels",
    "mid_deck_generated_panels",
    "mid_side_generated_panel",
    "mid_floor_generated_panels",
    "rear_side_generated_panels",
    "rear_floor_generated_panels",
    "rear_deck_fine_louver_rows",
]
PREMIUM_MASK_NAMES = [*PREMIUM_MASK_NAMES, *PANEL_FAMILY_MASK_NAMES]
PANEL_CATALOG_TARGETS = [
    "tailwing_bands",
    "side_wings",
    "mirrors_and_holders",
    "underbody_dark",
]
DEFAULT_PANEL_CATALOG_TARGETS = tuple(PANEL_CATALOG_TARGETS)


@dataclass(frozen=True)
class Candidate:
    name: str
    lane_id: str
    composition_focus: str
    distinctive_masks: tuple[str, ...]
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
    panel_catalog_targets: tuple[str, ...]
    mask_strengths: tuple[tuple[str, float], ...]


CANDIDATES = [
    Candidate(
        "black_magenta_cyan_blade",
        "side_blade_sweep",
        "wide lower side blades with a magenta nose spear and cyan side energy",
        ("side_blade", "secondary_blade", "nose_spear", "mudguard_edge"),
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
        (
            "sidepod_blades",
            "nose_identity_panel",
            "nose_side_generated_panels",
            "nose_deck_generated_panels",
            "nose_floor_generated_panels",
            "front_mudguard_caps",
            "front_mudguard_edge_details",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("side_blade", 1.32),
            ("secondary_blade", 1.18),
            ("nose_spear", 1.16),
            ("mudguard_edge", 1.20),
            ("rear_louvers", 0.62),
            ("rear_center_glow", 0.76),
        ),
    ),
    Candidate(
        "black_cyan_spine",
        "center_spine_focus",
        "dominant cyan center spine with magenta guard and tail echoes",
        ("center_spine", "nose_spear", "tailwing", "mudguard_edge"),
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
        (
            "center_spine",
            "nose_identity_panel",
            "mid_deck_generated_panels",
            "tailwing_bands",
            "front_mudguard_caps",
            "rear_mudguard_caps",
            "rear_mudguard_edge_details",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("center_spine", 1.34),
            ("nose_spear", 1.14),
            ("tailwing", 1.18),
            ("mudguard_edge", 1.12),
            ("side_blade", 0.58),
            ("secondary_blade", 0.62),
        ),
    ),
    Candidate(
        "violet_cyber_flow",
        "split_guard_flow",
        "violet/magenta flow with split guard color and cyan side structure",
        ("mudguards", "side_blade", "rear_center_glow", "tailwing"),
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
        (
            "sidepod_blades",
            "front_mudguard_caps",
            "rear_mudguard_caps",
            "front_mudguard_edge_details",
            "rear_mudguard_edge_details",
            "mid_side_generated_panel",
            "rear_side_generated_panels",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("mudguards", 1.28),
            ("side_blade", 1.16),
            ("rear_center_glow", 1.22),
            ("tailwing", 1.16),
            ("center_spine", 0.78),
        ),
    ),
    Candidate(
        "dark_neon_louver",
        "rear_louver_focus",
        "dense rear louver rhythm with restrained spine and alternating guard caps",
        ("rear_louvers", "rear_center_glow", "tail_bar", "tailwing"),
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
        (
            "engine_rear_deck",
            "rear_deck_fine_louver_rows",
            "rear_side_generated_panels",
            "rear_floor_generated_panels",
            "tailwing_bands",
            "rear_mudguard_caps",
            "rear_mudguard_edge_details",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("rear_louvers", 1.40),
            ("rear_center_glow", 1.26),
            ("tail_bar", 1.22),
            ("tailwing", 1.18),
            ("side_blade", 0.46),
            ("secondary_blade", 0.55),
            ("nose_spear", 0.70),
        ),
    ),
    Candidate(
        "magenta_cyan_race_proto",
        "race_proto_balance",
        "balanced race prototype layout using nose, spine, side blades, and local aero accents",
        ("nose_spear", "center_spine", "side_wings", "mirrors"),
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
        (
            "center_spine",
            "nose_identity_panel",
            "nose_deck_generated_panels",
            "mid_deck_generated_panels",
            "mid_side_generated_panel",
            "sidepod_blades",
            "side_wings",
            "mirrors_and_holders",
            "licence_plate_blocks",
            "tailwing_bands",
            "underbody_dark",
        ),
        (
            ("nose_spear", 1.22),
            ("center_spine", 1.16),
            ("side_wings", 1.25),
            ("mirrors", 1.28),
            ("rear_louvers", 0.72),
            ("rear_center_glow", 0.82),
        ),
    ),
]


def _candidate_catalog_targets(candidate: Candidate) -> list[str]:
    return list(dict.fromkeys(candidate.panel_catalog_targets))


def _candidate_mask_strengths(candidate: Candidate) -> dict[str, float]:
    strengths = {name: 1.0 for name in PREMIUM_MASK_NAMES}
    strengths.update({name: float(value) for name, value in candidate.mask_strengths})
    return strengths


def _candidate_panel_family_strengths(candidate: Candidate) -> dict[str, float]:
    targets = set(_candidate_catalog_targets(candidate))
    strengths: dict[str, float] = {}
    for name in PANEL_FAMILY_MASK_NAMES:
        if name in targets:
            strengths[name] = 1.0
    return strengths


def _blend_strength(strengths: dict[str, float], name: str, base: float) -> float:
    return base * strengths.get(name, 1.0)


def _panel_family_color(candidate: Candidate, name: str) -> str:
    if "floor" in name:
        return candidate.base2
    if "side" in name or "louver" in name:
        return candidate.secondary
    return candidate.primary


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
    amount = np.clip(_soft(mask) * strength, 0.0, 1.0)
    if amount.max() <= 0:
        return
    rgb[:] = rgb * (1.0 - amount[..., None]) + hx(color) * amount[..., None]


def _mask_params(candidate: Candidate) -> PremiumMaskParams:
    return PremiumMaskParams(
        spine_width=candidate.spine_width,
        blade_slope=candidate.blade_slope,
        blade_offset=candidate.blade_offset,
        rear_louver_count=candidate.rear_louver_count,
    )


def _build_masks(fields: dict[str, Any], candidate: Candidate) -> dict[str, np.ndarray]:
    panel_masks = build_stock_panel_masks(fields, _mask_params(candidate))
    return {name: panel.mask for name, panel in panel_masks.items()}


def build_premium_rgba(candidate: Candidate) -> tuple[Image.Image, dict[str, float], dict[str, dict[str, float | int]]]:
    fields = load_fields()
    coverage = fields["coverage"]
    labels = fields["labels"]
    length, _lateral, height, symmetry = _axis_fields(fields)
    masks = _build_masks(fields, candidate)
    strengths = _candidate_mask_strengths(candidate)
    panel_family_strengths = _candidate_panel_family_strengths(candidate)

    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    alpha = np.full((SIZE, SIZE), 112, dtype=np.float32)

    depth = 0.62 + 0.18 * length + 0.12 * height - 0.10 * np.clip(symmetry / 0.5, 0, 1)
    rgb[coverage] = hx(candidate.base)
    rgb[coverage] = rgb[coverage] * (1.0 - depth[coverage, None]) + hx(candidate.base2) * depth[coverage, None]

    _blend(rgb, masks["center_spine"], candidate.primary, _blend_strength(strengths, "center_spine", 0.95))
    _blend(rgb, masks["nose_spear"], candidate.primary, _blend_strength(strengths, "nose_spear", 1.00))
    _blend(rgb, masks["side_blade"], candidate.secondary, _blend_strength(strengths, "side_blade", 0.92))
    _blend(rgb, masks["secondary_blade"], candidate.primary, _blend_strength(strengths, "secondary_blade", 0.72))
    _blend(rgb, masks["rear_louvers"], candidate.secondary, _blend_strength(strengths, "rear_louvers", 0.86))
    _blend(rgb, masks["rear_center_glow"], candidate.primary, _blend_strength(strengths, "rear_center_glow", 0.82))
    _blend(rgb, masks["shoulder_line"], candidate.highlight, _blend_strength(strengths, "shoulder_line", 0.62))
    _blend(rgb, masks["tail_bar"], candidate.secondary, _blend_strength(strengths, "tail_bar", 0.95))

    underbody = masks["main_body_under"] | masks["underplate"]
    underbody_strength = max(strengths["main_body_under"], strengths["underplate"])
    _blend(rgb, underbody, "#020204", 0.42 * underbody_strength)
    _blend(rgb, masks["tailwing"], candidate.primary, _blend_strength(strengths, "tailwing", 0.34))
    _blend(rgb, masks["tailwing"] & (height > 0.52), candidate.secondary, _blend_strength(strengths, "tailwing", 0.28))
    _blend(rgb, masks["side_wings"], candidate.secondary, _blend_strength(strengths, "side_wings", 0.46))
    _blend(rgb, masks["mirrors"], candidate.highlight, _blend_strength(strengths, "mirrors", 0.54))

    panel_family_accent = np.zeros_like(coverage, dtype=bool)
    for mask_name, strength in panel_family_strengths.items():
        panel_family_accent |= masks[mask_name]
        _blend(rgb, masks[mask_name], _panel_family_color(candidate, mask_name), 0.18 * strength)

    if candidate.mudguard_mode == "split":
        _blend(rgb, masks["mudguards"] & (length > 0.5), candidate.primary, _blend_strength(strengths, "mudguards", 0.72))
        _blend(rgb, masks["mudguards"] & (length <= 0.5), candidate.secondary, _blend_strength(strengths, "mudguards", 0.72))
    elif candidate.mudguard_mode == "secondary_front":
        _blend(rgb, masks["mudguards"], candidate.primary, _blend_strength(strengths, "mudguards", 0.38))
        _blend(rgb, masks["mudguard_edge"] & (length > 0.5), candidate.secondary, _blend_strength(strengths, "mudguard_edge", 0.88))
        _blend(rgb, masks["mudguard_edge"] & (length <= 0.5), candidate.primary, _blend_strength(strengths, "mudguard_edge", 0.78))
    else:
        _blend(rgb, masks["mudguards"], candidate.secondary, _blend_strength(strengths, "mudguards", 0.38))
        _blend(rgb, masks["mudguard_edge"] & (length > 0.5), candidate.primary, _blend_strength(strengths, "mudguard_edge", 0.88))
        _blend(rgb, masks["mudguard_edge"] & (length <= 0.5), candidate.secondary, _blend_strength(strengths, "mudguard_edge", 0.78))

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
        | masks["tailwing"]
        | masks["side_wings"]
        | masks["mirrors"]
    )
    alpha[accent] = 148
    alpha[panel_family_accent & ~accent] = np.maximum(alpha[panel_family_accent & ~accent], 124)
    alpha[masks["shoulder_line"]] = 136
    alpha[underbody] = 118
    for mask_name in candidate.distinctive_masks:
        subtle_distinctive = masks[mask_name] & ~accent
        alpha[subtle_distinctive] = np.maximum(alpha[subtle_distinctive], 128)

    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    metrics = _style_metrics(out, coverage)
    mask_metrics = _mask_style_metrics(out, masks, PREMIUM_MASK_NAMES)
    return Image.fromarray(out, "RGBA"), metrics, mask_metrics


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


def _mask_style_metrics(
    rgba: np.ndarray,
    masks: dict[str, np.ndarray],
    names: list[str],
) -> dict[str, dict[str, float | int]]:
    rgb = rgba[..., :3].astype(np.float32)
    alpha = rgba[..., 3].astype(np.float32)
    lum = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    metrics: dict[str, dict[str, float | int]] = {}
    for name in names:
        mask = masks[name]
        pixel_count = int(mask.sum())
        if pixel_count == 0:
            metrics[name] = {
                "pixel_count": 0,
                "mean_alpha": 0.0,
                "mean_luminance": 0.0,
                "mean_chroma": 0.0,
                "high_alpha_pixel_ratio": 0.0,
            }
            continue
        mask_alpha = alpha[mask]
        metrics[name] = {
            "pixel_count": pixel_count,
            "mean_alpha": round(float(mask_alpha.mean()), 6),
            "mean_luminance": round(float(lum[mask].mean()), 6),
            "mean_chroma": round(float(chroma[mask].mean()), 6),
            "high_alpha_pixel_ratio": round(float((mask_alpha >= 136).sum() / pixel_count), 6),
        }
    return metrics


def _alpha_metrics(rgba: np.ndarray, coverage: np.ndarray) -> dict[str, float | int | list[int]]:
    alpha = rgba[..., 3][coverage].astype(np.uint8)
    if alpha.size == 0:
        return {
            "min_alpha": 0,
            "max_alpha": 0,
            "mean_alpha": 0.0,
            "unique_alpha_values": [],
            "high_alpha_pixel_ratio": 0.0,
        }
    return {
        "min_alpha": int(alpha.min()),
        "max_alpha": int(alpha.max()),
        "mean_alpha": round(float(alpha.mean()), 6),
        "unique_alpha_values": [int(value) for value in np.unique(alpha)],
        "high_alpha_pixel_ratio": round(float((alpha >= 136).sum() / alpha.size), 6),
    }


def _write_candidate(candidate: Candidate) -> dict[str, str]:
    out_skin = ROOT / "out" / "skins" / f"{candidate.name}.zip"
    out_preview = ROOT / "out" / "previews" / f"{candidate.name}_projected_side_top_rear.png"
    out_atlas = ROOT / "out" / "previews" / f"{candidate.name}_atlas.png"
    out_report = ROOT / "out" / "reports" / f"{candidate.name}.json"
    for path in (out_skin.parent, out_preview.parent, out_report.parent):
        path.mkdir(parents=True, exist_ok=True)

    image, metrics, mask_style_metrics = build_premium_rgba(candidate)
    fields = load_fields()
    alpha_metrics = _alpha_metrics(np.asarray(image), fields["coverage"])
    icon = image.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS).convert("RGBA")

    with zipfile.ZipFile(out_skin, "w", zipfile.ZIP_DEFLATED) as zf:
        write_stable_zip_entry(zf, "Diffuse.dds", build_dds_dxt5_bytes(image, mipmaps=True))
        write_stable_zip_entry(zf, "Icon.dds", build_dds_dxt5_bytes(icon, mipmaps=True))

    image.save(out_atlas)
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
    mask_strengths = _candidate_mask_strengths(candidate)
    panel_family_strengths = _candidate_panel_family_strengths(candidate)

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
        "input_evidence": input_evidence(PREMIUM_DIFFUSE_INPUTS),
        "output_artifacts": stock_output_artifacts(out_skin, out_atlas, out_preview),
        "design_lane": {
            "lane_id": candidate.lane_id,
            "composition_focus": candidate.composition_focus,
            "distinctive_masks": list(candidate.distinctive_masks),
            "primary_catalog_targets": _candidate_catalog_targets(candidate),
            "catalog_target_count": len(_candidate_catalog_targets(candidate)),
            "evidence_status": "recipe_metadata_not_tmuf_proof",
            "parameter_signature": {
                "spine_width": candidate.spine_width,
                "blade_slope": candidate.blade_slope,
                "blade_offset": candidate.blade_offset,
                "rear_louver_count": candidate.rear_louver_count,
                "mudguard_mode": candidate.mudguard_mode,
            },
        },
        "render_profile": {
            "lane_specific_strengths": True,
            "evidence_status": "recipe_metadata_not_tmuf_proof",
            "mask_strengths": mask_strengths,
            "panel_family_strengths": panel_family_strengths,
            "distinctive_mask_strengths": {
                name: mask_strengths[name] for name in candidate.distinctive_masks
            },
            "damped_masks": [
                name for name, strength in mask_strengths.items() if strength < 1.0
            ],
        },
        "alpha_policy": {
            "route": "conservative_dxt5_alpha",
            "material_effect_status": "not_proven_until_tmuf_smoke",
            "tmuf_gloss_claim": "none",
            "base_alpha": 112,
            "underbody_alpha": 118,
            "shoulder_alpha": 136,
            "accent_alpha": 148,
        },
        "alpha_metrics": alpha_metrics,
        "design_rules": [
            "black_charcoal_base",
            "magenta_cyan_accents",
            "broad_gbuffer_aligned_shapes",
            "symmetric_rear_engine_panels",
            "proven_local_panel_accents",
            "no_vignette",
            "no_random_scatter",
            "no_stadiumcar_v2_uvs",
            "no_ch2026_donor_assumptions",
        ],
        "panel_catalog_targets": _candidate_catalog_targets(candidate),
        "panel_visual_coverage": build_panel_visual_coverage(
            _candidate_catalog_targets(candidate),
            mask_style_metrics,
        ),
        "masks_used": PREMIUM_MASK_NAMES,
        "mask_evidence": mask_report_entries(
            build_stock_panel_masks(load_fields(), _mask_params(candidate)),
            PREMIUM_MASK_NAMES,
        ),
        "mask_style_metrics": mask_style_metrics,
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


def _batch_candidate_entry(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "skin_name": report["skin_name"],
        "route": report["route"],
        "package_files": report["package_files"],
        "tmuf_smoke_test": report["tmuf_smoke_test"],
        "gbuffer_mapping": report["evidence_status"]["gbuffer_mapping"],
        "design_lane": report["design_lane"],
        "render_profile": report["render_profile"],
        "style_metrics": report["style_metrics"],
        "alpha_metrics": report["alpha_metrics"],
        "panel_catalog_targets": report["panel_catalog_targets"],
        "output_artifacts": report["output_artifacts"],
    }


def write_batch_index(outputs: list[dict[str, str]]) -> Path:
    reports = [json.loads(Path(item["report"]).read_text()) for item in outputs]
    index = {
        "schema": "tmuf_premium_skin_lab.premium_batch_index.v1",
        "route": "stock_diffuse_only",
        "candidate_count": len(reports),
        "does_not_prove_tmuf_smoke": True,
        "tmuf_smoke_status": "pending",
        "gbuffer_mapping": "experimental_until_tmuf_smoke",
        "completion_status": "not_complete_tmuf_smoke_pending",
        "required_before_promotion": [
            "run_tmuf_calibration_smoke_test",
            "record_tmuf_smoke_evidence",
            "evaluate_then_apply_tmuf_smoke_gate",
        ],
        "candidates": [_batch_candidate_entry(report) for report in reports],
    }
    BATCH_INDEX.parent.mkdir(parents=True, exist_ok=True)
    BATCH_INDEX.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    return BATCH_INDEX


def save_batch() -> list[dict[str, str]]:
    outputs = [_write_candidate(candidate) for candidate in CANDIDATES]
    write_batch_index(outputs)
    return outputs


def main() -> int:
    outputs = save_batch()
    for item in outputs:
        print(f"wrote {item['zip']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
