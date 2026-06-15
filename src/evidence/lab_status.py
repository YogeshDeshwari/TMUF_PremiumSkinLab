from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.evidence.smoke_kit import DEFAULT_KIT_DIR, validate_smoke_kit
from src.evidence.stock_validator import validate_stock_outputs
from src.profiles.gates import evaluate_profile_gates
from src.stock_diffuse.premium import CANDIDATE_NAMES


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATUS_PATH = ROOT / "out" / "reports" / "lab_status.json"


def _smoke_kit_status(root: Path) -> dict[str, Any]:
    kit_dir = root / DEFAULT_KIT_DIR.relative_to(ROOT)
    validation = validate_smoke_kit(kit_dir)
    return {
        "exists": validation["exists"],
        "fresh": validation["fresh"],
        "status": validation["manifest_status"],
        "freshness_status": validation["status"],
        "manifest": validation["manifest"],
        "zip": validation["zip"],
        "missing_files": validation["missing_files"],
        "stale_files": validation["stale_files"],
        "zip_missing_or_stale": validation["zip_missing_or_stale"],
        "does_not_prove_tmuf_smoke": validation["does_not_prove_tmuf_smoke"],
    }


def build_lab_status(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    stock = validate_stock_outputs(root)
    profiles = evaluate_profile_gates(root)
    smoke_kit = _smoke_kit_status(root)

    blockers: list[str] = []
    next_required: list[str] = []
    if stock["tmuf_smoke_status"] != "passed":
        blockers.append("stock_calibration_tmuf_smoke_pending")
        next_required.append("run_tmuf_calibration_smoke_test")
        next_required.append("record_tmuf_smoke_evidence")
        next_required.append("fill_out/proof/calibration_tmuf_smoke.json")
        next_required.append("evaluate_then_apply_tmuf_smoke_gate")
    if profiles["overall_status"] == "custom_profiles_locked":
        blockers.append("custom_profiles_locked_until_stock_and_profile_smoke")

    objective_status = "complete" if not blockers and stock["completion_status"] == "complete" else "not_complete_tmuf_smoke_pending"
    return {
        "objective_status": objective_status,
        "goal_completion_blockers": blockers,
        "next_required_evidence": next_required,
        "stock": {
            "local_checks_passed": stock["local_checks_passed"],
            "tmuf_smoke_status": stock["tmuf_smoke_status"],
            "completion_status": stock["completion_status"],
            "candidate_count": len(CANDIDATE_NAMES),
            "errors": stock["errors"],
            "warnings": stock["warnings"],
        },
        "profiles": {
            "overall_status": profiles["overall_status"],
            "stock_calibration_gate": profiles["stock_calibration_gate"],
            "ch2026_fullcar": profiles["profiles"]["ch2026_fullcar"]["status"],
            "ch2026_nomud": profiles["profiles"]["ch2026_nomud"]["status"],
        },
        "smoke_kit": smoke_kit,
    }


def write_lab_status(path: Path = DEFAULT_STATUS_PATH, root: Path = ROOT) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_lab_status(root), indent=2, sort_keys=True) + "\n")
    return path
