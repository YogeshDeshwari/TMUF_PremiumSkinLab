from __future__ import annotations

from typing import Any


PANEL_TARGET_MASKS: dict[str, tuple[str, ...]] = {
    "center_spine": ("center_spine",),
    "nose_identity_panel": ("nose_spear",),
    "nose_deck_generated_panels": ("nose_deck_generated_panels",),
    "nose_floor_generated_panels": ("nose_floor_generated_panels",),
    "nose_side_generated_panels": ("nose_side_generated_panels",),
    "mid_deck_generated_panels": ("mid_deck_generated_panels",),
    "mid_side_generated_panel": ("mid_side_generated_panel",),
    "mid_floor_generated_panels": ("mid_floor_generated_panels",),
    "rear_side_generated_panels": ("rear_side_generated_panels",),
    "rear_floor_generated_panels": ("rear_floor_generated_panels",),
    "rear_deck_fine_louver_rows": ("rear_deck_fine_louver_rows", "rear_louvers"),
    "sidepod_blades": ("side_blade", "secondary_blade"),
    "engine_rear_deck": ("rear_louvers", "rear_center_glow", "tail_bar"),
    "tailwing_bands": ("tailwing", "tail_bar"),
    "side_wings": ("side_wings",),
    "mirrors_and_holders": ("mirrors",),
    "underbody_dark": ("main_body_under", "underplate"),
    "front_mudguard_caps": ("mudguards",),
    "rear_mudguard_caps": ("mudguards",),
    "front_mudguard_edge_details": ("mudguard_edge",),
    "rear_mudguard_edge_details": ("mudguard_edge",),
    "licence_plate_blocks": (),
    "rear_wheel_diffuse_blocks": (),
    "helmet_and_visor": (),
    "main_body_top_quadrants": (),
    "side_vent_inside": (),
}

PANEL_VISUAL_COVERAGE_SCHEMA = "tmuf_premium_skin_lab.panel_visual_coverage.v1"
PANEL_VISUAL_COVERAGE_STATUS = "local_preview_metric_not_tmuf_proof"
ACTIVATION_RULE = "accent_or_alpha_or_dark_support"
UNMAPPED_RULE = "not_mapped_to_renderer_mask"


def build_panel_visual_coverage(
    panel_catalog_targets: list[str],
    mask_style_metrics: dict[str, dict[str, float | int]],
) -> dict[str, Any]:
    target_entries = {
        target: _target_entry(target, mask_style_metrics)
        for target in panel_catalog_targets
    }
    mapped_count = sum(1 for entry in target_entries.values() if entry["mapped"])
    return {
        "schema": PANEL_VISUAL_COVERAGE_SCHEMA,
        "evidence_status": PANEL_VISUAL_COVERAGE_STATUS,
        "does_not_prove_tmuf_smoke": True,
        "boundary": "Local atlas/render-mask coverage only; this does not prove TMUF runtime visibility, seam quality, or GBuffer mapping.",
        "activation_rule": ACTIVATION_RULE,
        "mapped_target_count": mapped_count,
        "unmapped_target_count": len(target_entries) - mapped_count,
        "targets": target_entries,
    }


def _target_entry(
    target: str,
    mask_style_metrics: dict[str, dict[str, float | int]],
) -> dict[str, Any]:
    mask_names = PANEL_TARGET_MASKS.get(target, ())
    if not mask_names:
        return {
            "target": target,
            "mapped": False,
            "mask_names": [],
            "pixel_count": 0,
            "max_mean_alpha": 0.0,
            "max_mean_chroma": 0.0,
            "min_mean_luminance": 0.0,
            "max_high_alpha_pixel_ratio": 0.0,
            "visual_active": False,
            "activation_rule": UNMAPPED_RULE,
        }

    metrics = [
        mask_style_metrics[name]
        for name in mask_names
        if name in mask_style_metrics and isinstance(mask_style_metrics[name], dict)
    ]
    pixel_count = int(sum(int(entry.get("pixel_count", 0)) for entry in metrics))
    max_alpha = max((float(entry.get("mean_alpha", 0.0)) for entry in metrics), default=0.0)
    max_chroma = max((float(entry.get("mean_chroma", 0.0)) for entry in metrics), default=0.0)
    min_luminance = min((float(entry.get("mean_luminance", 999.0)) for entry in metrics), default=0.0)
    max_high_alpha = max((float(entry.get("high_alpha_pixel_ratio", 0.0)) for entry in metrics), default=0.0)
    visual_active = bool(
        pixel_count > 0
        and (
            max_alpha > 116.0
            or max_chroma >= 24.0
            or min_luminance <= 45.0
            or max_high_alpha >= 0.08
        )
    )
    return {
        "target": target,
        "mapped": True,
        "mask_names": list(mask_names),
        "pixel_count": pixel_count,
        "max_mean_alpha": round(max_alpha, 6),
        "max_mean_chroma": round(max_chroma, 6),
        "min_mean_luminance": round(min_luminance, 6),
        "max_high_alpha_pixel_ratio": round(max_high_alpha, 6),
        "visual_active": visual_active,
        "activation_rule": ACTIVATION_RULE,
    }
