from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REFERENCE_INDEX = ROOT / "out" / "reference_analysis" / "reference_package_index.json"
DEFAULT_GUIDANCE = ROOT / "out" / "reports" / "reference_style_guidance.json"
SCHEMA = "tmuf_premium_skin_lab.reference_style_guidance.v1"
GUIDANCE_STATUS = "reference_metrics_not_tmuf_proof"
RECOMMENDED_RULES = [
    "black_gray_white_base",
    "magenta_high_value_accent",
    "cyan_secondary_contrast",
    "red_separate_lane_not_first_bmc_family",
]


def build_reference_style_guidance(reference_index: Path = DEFAULT_REFERENCE_INDEX) -> dict[str, Any]:
    reference_index = Path(reference_index)
    index = json.loads(reference_index.read_text())
    reports = [_load_report(item, reference_index) for item in index.get("reports", [])]
    scored = [_score_report(report) for report in reports]
    scored = [entry for entry in scored if entry is not None]
    scored.sort(key=lambda entry: entry["black_magenta_cyan_score"], reverse=True)

    return {
        "schema": SCHEMA,
        "source_index": _repo_rel(reference_index),
        "source_report_count": len(reports),
        "evidence_status": GUIDANCE_STATUS,
        "does_not_prove_tmuf_smoke": True,
        "does_not_prove_stock_diffuse_mapping": True,
        "route_counts": index.get("route_counts", {}),
        "palette_tag_counts": index.get("palette_tag_counts", {}),
        "recommended_stock_design_rules": RECOMMENDED_RULES,
        "closest_black_magenta_cyan_references": scored[:5],
        "generator_guidance": {
            "base_family": "black_gray_white",
            "primary_accent": "magenta",
            "secondary_accent": "cyan",
            "magenta_policy": "high_value_accent_not_full_surface_flood",
            "cyan_policy": "secondary_blades_spines_and_cold_light_contrast",
            "red_policy": "separate_recipe_lane_not_first_black_magenta_cyan_family",
            "scope": "stock Diffuse recipe metadata only; not stock UV or TMUF runtime proof",
        },
    }


def write_reference_style_guidance(
    reference_index: Path = DEFAULT_REFERENCE_INDEX,
    output_path: Path = DEFAULT_GUIDANCE,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    guidance = build_reference_style_guidance(reference_index)
    output_path.write_text(json.dumps(guidance, indent=2, sort_keys=True) + "\n")
    return output_path


def guidance_report_block(guidance: dict[str, Any], output_path: Path = DEFAULT_GUIDANCE) -> dict[str, Any]:
    return {
        "path": _repo_rel(output_path),
        "evidence_status": guidance.get("evidence_status", GUIDANCE_STATUS),
        "does_not_prove_tmuf_smoke": True,
        "does_not_prove_stock_diffuse_mapping": True,
        "applied_rules": list(guidance.get("recommended_stock_design_rules", [])),
        "closest_reference_packages": [
            item["package_name"]
            for item in guidance.get("closest_black_magenta_cyan_references", [])[:3]
            if "package_name" in item
        ],
        "generator_guidance": guidance.get("generator_guidance", {}),
    }


def _load_report(item: dict[str, Any], reference_index: Path) -> dict[str, Any]:
    report_path = Path(item["report"])
    if not report_path.is_absolute():
        root_candidate = ROOT / report_path
        index_candidate = reference_index.parent / report_path
        report_path = root_candidate if root_candidate.exists() else index_candidate
    return json.loads(report_path.read_text())


def _score_report(report: dict[str, Any]) -> dict[str, Any] | None:
    metrics = report.get("style_metrics", {})
    primary = metrics.get("primary_livery_slot")
    slots = metrics.get("slots", {})
    if not isinstance(primary, str) or primary not in slots:
        return None
    slot = slots[primary]
    black = float(slot.get("black_ratio", 0.0))
    magenta = float(slot.get("magenta_ratio", 0.0))
    cyan = float(slot.get("cyan_ratio", 0.0))
    red = float(slot.get("red_ratio", 0.0))
    contrast = float(slot.get("mean_contrast", 0.0))
    score = black * 0.45 + magenta * 1.35 + cyan * 1.35 + min(contrast / 255.0, 1.0) * 0.35
    return {
        "package_name": report.get("package_name", "unknown"),
        "package_route": report.get("package_route", "unknown"),
        "stock_lane_status": report.get("stock_lane_status", "unknown"),
        "primary_livery_slot": primary,
        "black_magenta_cyan_score": round(score, 6),
        "black_ratio": round(black, 6),
        "magenta_ratio": round(magenta, 6),
        "cyan_ratio": round(cyan, 6),
        "red_ratio": round(red, 6),
        "mean_contrast": round(contrast, 6),
        "alpha_visible_ratio": round(float(slot.get("alpha_visible_ratio", 0.0)), 6),
        "palette_tags": list(slot.get("palette_tags", [])),
        "safe_use": "reference_only_visual_style_guidance_not_stock_truth",
    }


def _repo_rel(path: Path) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()
