from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.evidence.input_trace import MANIFEST
from src.evidence.stock_validator import validate_stock_outputs


ROOT = Path(__file__).resolve().parents[2]
CH2026_DONOR = "experimental/base_car/CH_2026_NOT_STOCK_STADIUM_DETAILS_CUSTOM_MESH.zip"
REMOVE_GUARDS_DLL = "experimental/flows/remove_guards/bin/Release/net9.0/remove_guards.dll"


def _manifest_entries(root: Path) -> dict[str, dict[str, Any]]:
    data = json.loads((root / MANIFEST.relative_to(ROOT)).read_text())
    return {entry["path"]: entry for entry in data["resources"]}


def _input_entry(entries: dict[str, dict[str, Any]], path: str) -> dict[str, Any]:
    entry = entries[path]
    return {
        "evidence_label": entry["evidence_label"],
        "sha256": entry["sha256"],
        "size_bytes": entry["size_bytes"],
        "safe_use": entry["safe_use"],
        "limits": entry["limits"],
    }


def _stock_passed(root: Path) -> bool:
    result = validate_stock_outputs(root)
    return result["tmuf_smoke_status"] == "passed"


def evaluate_profile_gates(
    root: Path = ROOT,
    stock_calibration_passed: bool | None = None,
    ch2026_fullcar_passed: bool = False,
) -> dict[str, Any]:
    root = Path(root)
    entries = _manifest_entries(root)
    stock_passed = _stock_passed(root) if stock_calibration_passed is None else stock_calibration_passed

    fullcar_reasons: list[str] = []
    if not stock_passed:
        fullcar_reasons.append("stock_calibration_tmuf_smoke_pending")

    if ch2026_fullcar_passed:
        fullcar_status = "proven"
    elif stock_passed:
        fullcar_status = "ready_for_experimental_build"
    else:
        fullcar_status = "locked"

    nomud_reasons: list[str] = []
    if not ch2026_fullcar_passed:
        nomud_reasons.append("ch2026_fullcar_not_proven")
    nomud_reasons.append("nomud_tmuf_smoke_missing")
    nomud_status = "ready_for_experimental_build" if ch2026_fullcar_passed else "locked"

    profiles = {
        "ch2026_fullcar": {
            "status": fullcar_status,
            "reasons": fullcar_reasons,
            "inputs": {CH2026_DONOR: _input_entry(entries, CH2026_DONOR)},
            "allowed_outputs_after_unlock": [
                "GBX files",
                "Diffuse.dds",
                "Details.dds",
                "Icon.dds",
                "optional ProjShad.dds",
            ],
            "proof_required": [
                "stock_calibration_tmuf_smoke_passed",
                "ch2026_fullcar_package_build_report",
                "ch2026_fullcar_tmuf_smoke_passed",
            ],
            "scope": "CH_2026 donor/custom mesh only; not stock StadiumCar truth.",
        },
        "ch2026_nomud": {
            "status": nomud_status,
            "reasons": nomud_reasons,
            "inputs": {
                CH2026_DONOR: _input_entry(entries, CH2026_DONOR),
                REMOVE_GUARDS_DLL: _input_entry(entries, REMOVE_GUARDS_DLL),
            },
            "allowed_outputs_after_unlock": [
                "CH_2026 GBX files with high-mesh guard-removal attempt",
                "Diffuse.dds",
                "Details.dds",
                "Icon.dds",
                "optional ProjShad.dds",
            ],
            "known_evidence": [
                "remove_guards_high_mesh_removes_6_low_mesh_removes_0",
            ],
            "proof_required": [
                "ch2026_fullcar_tmuf_smoke_passed",
                "nomud_package_build_report",
                "nomud_tmuf_smoke_passed",
            ],
            "scope": "No-mudguard remains CH_2026-specific and experimental.",
        },
    }

    locked = [profile for profile in profiles.values() if profile["status"] == "locked"]
    return {
        "overall_status": "custom_profiles_locked" if locked else "custom_profiles_ready_for_experimental_build",
        "stock_calibration_gate": "passed" if stock_passed else "pending_tmuf_smoke",
        "profiles": profiles,
    }
