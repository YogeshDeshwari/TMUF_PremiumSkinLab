from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEMPLATE = ROOT / "out" / "proof" / "calibration_tmuf_smoke_template.json"
DEFAULT_REPORTS_DIR = ROOT / "out" / "reports"
CALIBRATION_ARTIFACT = "out/skins/calibration_stock_diffuse.zip"
INSTALL_RECEIPT_SCHEMA = "tmuf_premium_skin_lab.calibration_install_receipt.v1"
INSTALL_RECEIPT_ROUTES = {
    "skins_vehicles_stadiumcar",
    "gamedata_skins_vehicles_stadiumcar",
    "skins_models_stadiumcar",
}
REQUIRED_OBSERVATIONS = [
    "nose_is_red",
    "tail_is_blue",
    "left_side_is_green",
    "right_side_is_yellow",
    "roof_high_surfaces_are_white",
    "lower_floor_surfaces_are_dark",
    "mudguards_are_magenta",
    "centerline_is_cyan",
    "package_loads_without_custom_gbx",
]
REQUIRED_METADATA = ["tester", "tmuf_build", "test_date_local"]
REQUIRED_SCREENSHOT_ROLES = ["front", "side", "rear", "top"]
PROMOTABLE_GBUFFER_MASK_STATUSES = {
    "experimental_until_tmuf_smoke",
    "mixed_generated_labels_and_experimental_gbuffer",
    "mixed_local_label_and_experimental_gbuffer",
}


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def validate_screenshot_file(path: Path) -> dict[str, Any]:
    path = Path(path)
    try:
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            extrema = rgb.getextrema()
            width, height = rgb.size
    except (OSError, UnidentifiedImageError):
        return {"readable": False, "nonblank": False, "size": None}

    nonblank = any(channel_min != channel_max for channel_min, channel_max in extrema)
    return {"readable": True, "nonblank": nonblank, "size": [width, height]}


def fingerprint_screenshot_file(path: Path) -> dict[str, Any]:
    path = Path(path)
    validation = validate_screenshot_file(path)
    if not validation["readable"]:
        raise ValueError(f"Screenshot must be a readable image: {path}")
    if not validation["nonblank"]:
        raise ValueError(f"Screenshot must be nonblank: {path}")
    size = validation["size"] or [0, 0]
    return {
        "sha256": _file_sha256(path),
        "size_bytes": path.stat().st_size,
        "width": size[0],
        "height": size[1],
    }


def validate_install_receipt_file(path: Path, base_dir: Path | None = None) -> dict[str, Any]:
    path = Path(path)
    base = Path(base_dir) if base_dir is not None else ROOT
    errors: list[str] = []
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {
            "readable": False,
            "valid": False,
            "errors": ["receipt_not_readable_json"],
            "receipt_sha256": None,
            "receipt_size_bytes": None,
        }

    schema = data.get("schema")
    if schema != INSTALL_RECEIPT_SCHEMA:
        errors.append("schema_mismatch")
    status = data.get("status")
    if status != "installed_not_tested":
        errors.append("status_not_installed_not_tested")
    route = data.get("route")
    if route not in INSTALL_RECEIPT_ROUTES:
        errors.append("unknown_route")
    if data.get("does_not_prove_tmuf_smoke") is not True:
        errors.append("receipt_must_not_claim_smoke_proof")

    installed_value = str(data.get("installed_skin", "")).strip()
    installed_sha256 = None
    installed_size_bytes = None
    if installed_value:
        installed_path = _resolve_evidence_path(installed_value, base)
        if installed_path.is_file():
            installed_sha256 = _file_sha256(installed_path)
            installed_size_bytes = installed_path.stat().st_size
        else:
            errors.append("installed_skin_missing")
    else:
        installed_path = None
        errors.append("installed_skin_missing")

    receipt_sha256 = str(data.get("sha256", "")).strip()
    source_sha256 = str(data.get("source_sha256", "")).strip()
    if installed_sha256 and receipt_sha256 != installed_sha256:
        errors.append("installed_sha256_mismatch")
    if installed_sha256 and source_sha256 != installed_sha256:
        errors.append("source_sha256_mismatch")

    return {
        "readable": True,
        "valid": not errors,
        "errors": errors,
        "schema": schema,
        "status": status,
        "route": route,
        "installed_skin": installed_value,
        "installed_sha256": installed_sha256,
        "installed_size_bytes": installed_size_bytes,
        "source_sha256": source_sha256,
        "receipt_declared_sha256": receipt_sha256,
        "receipt_sha256": _file_sha256(path),
        "receipt_size_bytes": path.stat().st_size,
    }


def fingerprint_install_receipt_file(path: Path, base_dir: Path | None = None) -> dict[str, Any]:
    validation = validate_install_receipt_file(path, base_dir=base_dir)
    if not validation["readable"]:
        raise ValueError(f"Install receipt must be readable JSON: {path}")
    if not validation["valid"]:
        raise ValueError(f"Install receipt is invalid: {validation['errors']}")
    return {
        "receipt_sha256": validation["receipt_sha256"],
        "receipt_size_bytes": validation["receipt_size_bytes"],
        "installed_skin": validation["installed_skin"],
        "installed_sha256": validation["installed_sha256"],
        "installed_size_bytes": validation["installed_size_bytes"],
        "source_sha256": validation["source_sha256"],
        "route": validation["route"],
        "status": validation["status"],
    }


def write_template(path: Path = DEFAULT_TEMPLATE) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "schema_version": 1,
        "artifact": CALIBRATION_ARTIFACT,
        "route": "stock_diffuse_only",
        "status": "not_run",
        "tester": "",
        "tmuf_build": "",
        "test_date_local": "",
        "screenshots": [],
        "screenshot_roles": {role: "" for role in REQUIRED_SCREENSHOT_ROLES},
        "install_receipt": "",
        "install_receipt_evidence": {},
        "observations": {name: False for name in REQUIRED_OBSERVATIONS},
        "notes": "",
        "pass_requires": [
            "Set status to passed only after loading the calibration zip in TMUF/TMNF.",
            "Every required observation must be true.",
            "The front, side, rear, and top screenshot roles must each reference a readable, nonblank image.",
            "Recorded screenshot fingerprints must match the current screenshot files.",
            "If an install receipt is included, its copied calibration zip hash must still match the receipt.",
            "This gate proves GBuffer mapping for this stock Diffuse route only.",
        ],
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return path


def _resolve_evidence_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path


def evaluate_smoke_report(path: Path, base_dir: Path | None = None) -> dict[str, Any]:
    path = Path(path)
    data = json.loads(path.read_text())
    base = Path(base_dir) if base_dir is not None else ROOT

    observations = data.get("observations", {})
    missing_observations = [name for name in REQUIRED_OBSERVATIONS if observations.get(name) is not True]
    missing_metadata = [name for name in REQUIRED_METADATA if not str(data.get(name, "")).strip()]

    raw_screenshot_roles = data.get("screenshot_roles", {})
    if not isinstance(raw_screenshot_roles, dict):
        raw_screenshot_roles = {}
    screenshot_roles = {
        str(role): str(path)
        for role, path in raw_screenshot_roles.items()
        if str(path).strip()
    }
    missing_screenshot_roles = [
        role for role in REQUIRED_SCREENSHOT_ROLES if role not in screenshot_roles
    ]
    screenshots = [screenshot_roles[role] for role in REQUIRED_SCREENSHOT_ROLES if role in screenshot_roles]
    missing_screenshots = [
        item for item in screenshots if not _resolve_evidence_path(item, base).exists()
    ]
    screenshot_validation = {
        item: validate_screenshot_file(_resolve_evidence_path(item, base))
        for item in screenshots
        if item not in missing_screenshots
    }
    invalid_screenshots = [
        item for item, validation in screenshot_validation.items() if not validation["readable"]
    ]
    blank_screenshots = [
        item
        for item, validation in screenshot_validation.items()
        if validation["readable"] and not validation["nonblank"]
    ]
    screenshot_evidence = data.get("screenshot_evidence", {})
    if not isinstance(screenshot_evidence, dict):
        screenshot_evidence = {}
    current_fingerprints = {
        item: fingerprint_screenshot_file(_resolve_evidence_path(item, base))
        for item in screenshots
        if item not in missing_screenshots and item not in invalid_screenshots and item not in blank_screenshots
    }
    missing_screenshot_fingerprints = [
        item for item in screenshots if item not in missing_screenshots and item not in screenshot_evidence
    ]
    mismatched_screenshot_fingerprints = [
        item
        for item, fingerprint in current_fingerprints.items()
        if item in screenshot_evidence and screenshot_evidence[item] != fingerprint
    ]
    has_valid_screenshot = (
        not missing_screenshot_roles
        and not missing_screenshots
        and not invalid_screenshots
        and not blank_screenshots
        and not missing_screenshot_fingerprints
        and not mismatched_screenshot_fingerprints
    )

    install_receipt = str(data.get("install_receipt", "")).strip()
    raw_install_receipt_evidence = data.get("install_receipt_evidence", {})
    if not isinstance(raw_install_receipt_evidence, dict):
        raw_install_receipt_evidence = {}
    missing_install_receipts: list[str] = []
    invalid_install_receipts: list[str] = []
    install_receipt_validation: dict[str, Any] = {}
    current_install_receipt_fingerprints: dict[str, dict[str, Any]] = {}
    missing_install_receipt_fingerprints: list[str] = []
    mismatched_install_receipt_fingerprints: list[str] = []
    if install_receipt:
        receipt_path = _resolve_evidence_path(install_receipt, base)
        if not receipt_path.exists():
            missing_install_receipts.append(install_receipt)
        else:
            validation = validate_install_receipt_file(receipt_path, base_dir=base)
            install_receipt_validation[install_receipt] = validation
            if not validation["valid"]:
                invalid_install_receipts.append(install_receipt)
            else:
                current = fingerprint_install_receipt_file(receipt_path, base_dir=base)
                current_install_receipt_fingerprints[install_receipt] = current
                if not raw_install_receipt_evidence:
                    missing_install_receipt_fingerprints.append(install_receipt)
                elif raw_install_receipt_evidence != current:
                    mismatched_install_receipt_fingerprints.append(install_receipt)
    elif raw_install_receipt_evidence:
        invalid_install_receipts.append("install_receipt_evidence_without_install_receipt")

    passed = (
        data.get("status") == "passed"
        and data.get("artifact") == CALIBRATION_ARTIFACT
        and not missing_observations
        and not missing_metadata
        and has_valid_screenshot
        and not missing_install_receipts
        and not invalid_install_receipts
        and not missing_install_receipt_fingerprints
        and not mismatched_install_receipt_fingerprints
    )

    return {
        "passed": passed,
        "status": "passed" if passed else "not_passed",
        "artifact": data.get("artifact"),
        "missing_observations": missing_observations,
        "missing_metadata": missing_metadata,
        "screenshots": screenshots,
        "screenshot_roles": screenshot_roles,
        "missing_screenshot_roles": missing_screenshot_roles,
        "missing_screenshots": missing_screenshots,
        "invalid_screenshots": invalid_screenshots,
        "blank_screenshots": blank_screenshots,
        "screenshot_validation": screenshot_validation,
        "screenshot_evidence": screenshot_evidence,
        "current_screenshot_fingerprints": current_fingerprints,
        "missing_screenshot_fingerprints": missing_screenshot_fingerprints,
        "mismatched_screenshot_fingerprints": mismatched_screenshot_fingerprints,
        "install_receipt": install_receipt,
        "install_receipt_evidence": raw_install_receipt_evidence,
        "install_receipt_validation": install_receipt_validation,
        "current_install_receipt_fingerprints": current_install_receipt_fingerprints,
        "missing_install_receipts": missing_install_receipts,
        "invalid_install_receipts": invalid_install_receipts,
        "missing_install_receipt_fingerprints": missing_install_receipt_fingerprints,
        "mismatched_install_receipt_fingerprints": mismatched_install_receipt_fingerprints,
        "gbuffer_mapping_status": "proven_by_tmuf_smoke" if passed else "experimental_until_tmuf_smoke",
        "tester": data.get("tester", ""),
        "tmuf_build": data.get("tmuf_build", ""),
        "test_date_local": data.get("test_date_local", ""),
    }


def apply_smoke_result(
    smoke_report_path: Path,
    report_paths: list[Path] | None = None,
    base_dir: Path | None = None,
) -> list[Path]:
    smoke_report_path = Path(smoke_report_path)
    result = evaluate_smoke_report(smoke_report_path, base_dir=base_dir)
    _raise_if_smoke_failed(result)

    paths = _apply_report_paths(report_paths)
    updated: list[Path] = []
    for path in paths:
        data = json.loads(path.read_text())
        if _is_stock_skin_report(data):
            _promote_stock_skin_report(data, result, smoke_report_path)
        elif _is_premium_batch_index(data):
            _promote_premium_batch_index(data, result, smoke_report_path)
        else:
            continue
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        updated.append(path)
    return updated


def plan_smoke_result(
    smoke_report_path: Path,
    report_paths: list[Path] | None = None,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    smoke_report_path = Path(smoke_report_path)
    result = evaluate_smoke_report(smoke_report_path, base_dir=base_dir)
    _raise_if_smoke_failed(result)

    would_update: list[dict[str, str]] = []
    would_skip: list[dict[str, str]] = []
    for path in _apply_report_paths(report_paths):
        data = json.loads(path.read_text())
        if _is_stock_skin_report(data):
            would_update.append({"path": str(path), "kind": "stock_skin_report"})
        elif _is_premium_batch_index(data):
            would_update.append({"path": str(path), "kind": "premium_batch_index"})
        else:
            would_skip.append({"path": str(path), "reason": "not_promotable_report"})

    return {
        "passed": True,
        "dry_run": True,
        "gbuffer_mapping_status": result["gbuffer_mapping_status"],
        "smoke_report": smoke_report_path.as_posix(),
        "would_update": would_update,
        "would_skip": would_skip,
    }


def _raise_if_smoke_failed(result: dict[str, Any]) -> None:
    if result["passed"]:
        return
    raise ValueError(
        "TMUF smoke evidence did not pass; reports remain experimental. "
        f"Missing observations: {result['missing_observations']}; "
        f"missing metadata: {result['missing_metadata']}; "
        f"missing screenshot roles: {result['missing_screenshot_roles']}; "
        f"missing screenshots: {result['missing_screenshots']}; "
        f"invalid screenshots: {result['invalid_screenshots']}; "
        f"blank screenshots: {result['blank_screenshots']}; "
        f"missing screenshot fingerprints: {result['missing_screenshot_fingerprints']}; "
        f"mismatched screenshot fingerprints: {result['mismatched_screenshot_fingerprints']}; "
        f"missing install receipts: {result['missing_install_receipts']}; "
        f"invalid install receipts: {result['invalid_install_receipts']}; "
        f"missing install receipt fingerprints: {result['missing_install_receipt_fingerprints']}; "
        f"mismatched install receipt fingerprints: {result['mismatched_install_receipt_fingerprints']}"
    )


def _apply_report_paths(report_paths: list[Path] | None = None) -> list[Path]:
    return (
        [Path(path) for path in report_paths]
        if report_paths is not None
        else sorted(DEFAULT_REPORTS_DIR.glob("*.json"))
    )


def _is_stock_skin_report(data: dict[str, Any]) -> bool:
    return (
        isinstance(data.get("skin_name"), str)
        and data.get("route") == "stock_diffuse_only"
        and data.get("package_files") == ["Diffuse.dds", "Icon.dds"]
        and data.get("supplemental_smoke_artifact") is not True
    )


def _is_premium_batch_index(data: dict[str, Any]) -> bool:
    return data.get("schema") == "tmuf_premium_skin_lab.premium_batch_index.v1"


def _smoke_evidence_payload(result: dict[str, Any], smoke_report_path: Path) -> dict[str, Any]:
    return {
        "report": smoke_report_path.as_posix(),
        "screenshots": result["screenshots"],
        "screenshot_roles": result["screenshot_roles"],
        "screenshot_evidence": result["screenshot_evidence"],
        "install_receipt": result["install_receipt"],
        "install_receipt_evidence": result["install_receipt_evidence"],
        "tester": result["tester"],
        "tmuf_build": result["tmuf_build"],
        "test_date_local": result["test_date_local"],
    }


def _promote_stock_skin_report(data: dict[str, Any], result: dict[str, Any], smoke_report_path: Path) -> None:
    evidence = data.setdefault("evidence_status", {})
    evidence["gbuffer_mapping"] = result["gbuffer_mapping_status"]
    _promote_gbuffer_mask_evidence(data, result["gbuffer_mapping_status"])
    data["tmuf_smoke_test"] = "passed"
    if isinstance(data.get("proof_gate"), dict):
        data["proof_gate"]["calibration_stock_diffuse"] = "passed"
    data["tmuf_smoke_evidence"] = _smoke_evidence_payload(result, smoke_report_path)


def _promote_premium_batch_index(data: dict[str, Any], result: dict[str, Any], smoke_report_path: Path) -> None:
    data["does_not_prove_tmuf_smoke"] = False
    data["tmuf_smoke_status"] = "passed"
    data["gbuffer_mapping"] = result["gbuffer_mapping_status"]
    data["completion_status"] = "stock_calibration_smoke_passed"
    data["required_before_promotion"] = []
    data["tmuf_smoke_evidence"] = _smoke_evidence_payload(result, smoke_report_path)
    for candidate in data.get("candidates", []):
        if isinstance(candidate, dict):
            candidate["tmuf_smoke_test"] = "passed"
            candidate["gbuffer_mapping"] = result["gbuffer_mapping_status"]


def _promote_gbuffer_mask_evidence(data: dict[str, Any], gbuffer_mapping_status: str) -> None:
    if gbuffer_mapping_status != "proven_by_tmuf_smoke":
        return
    mask_evidence = data.get("mask_evidence")
    if not isinstance(mask_evidence, dict):
        return
    for entry in mask_evidence.values():
        if (
            isinstance(entry, dict)
            and entry.get("evidence_status") in PROMOTABLE_GBUFFER_MASK_STATUSES
        ):
            entry["evidence_status"] = "proven_by_tmuf_smoke"
