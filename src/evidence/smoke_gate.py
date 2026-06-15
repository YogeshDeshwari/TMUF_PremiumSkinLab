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
        "sha256": sha256(path.read_bytes()).hexdigest(),
        "size_bytes": path.stat().st_size,
        "width": size[0],
        "height": size[1],
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
        "observations": {name: False for name in REQUIRED_OBSERVATIONS},
        "notes": "",
        "pass_requires": [
            "Set status to passed only after loading the calibration zip in TMUF/TMNF.",
            "Every required observation must be true.",
            "At least one referenced screenshot file must exist and be a readable, nonblank image.",
            "Recorded screenshot fingerprints must match the current screenshot files.",
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

    screenshots = [str(item) for item in data.get("screenshots", [])]
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
        bool(screenshots)
        and not missing_screenshots
        and not invalid_screenshots
        and not blank_screenshots
        and not missing_screenshot_fingerprints
        and not mismatched_screenshot_fingerprints
    )

    passed = (
        data.get("status") == "passed"
        and data.get("artifact") == CALIBRATION_ARTIFACT
        and not missing_observations
        and not missing_metadata
        and has_valid_screenshot
    )

    return {
        "passed": passed,
        "status": "passed" if passed else "not_passed",
        "artifact": data.get("artifact"),
        "missing_observations": missing_observations,
        "missing_metadata": missing_metadata,
        "screenshots": screenshots,
        "missing_screenshots": missing_screenshots,
        "invalid_screenshots": invalid_screenshots,
        "blank_screenshots": blank_screenshots,
        "screenshot_validation": screenshot_validation,
        "screenshot_evidence": screenshot_evidence,
        "current_screenshot_fingerprints": current_fingerprints,
        "missing_screenshot_fingerprints": missing_screenshot_fingerprints,
        "mismatched_screenshot_fingerprints": mismatched_screenshot_fingerprints,
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
    if not result["passed"]:
        raise ValueError(
            "TMUF smoke evidence did not pass; reports remain experimental. "
            f"Missing observations: {result['missing_observations']}; "
            f"missing metadata: {result['missing_metadata']}; "
            f"missing screenshots: {result['missing_screenshots']}; "
            f"invalid screenshots: {result['invalid_screenshots']}; "
            f"blank screenshots: {result['blank_screenshots']}; "
            f"missing screenshot fingerprints: {result['missing_screenshot_fingerprints']}; "
            f"mismatched screenshot fingerprints: {result['mismatched_screenshot_fingerprints']}"
        )

    paths = (
        [Path(path) for path in report_paths]
        if report_paths is not None
        else sorted(DEFAULT_REPORTS_DIR.glob("*.json"))
    )
    updated: list[Path] = []
    for path in paths:
        data = json.loads(path.read_text())
        evidence = data.setdefault("evidence_status", {})
        evidence["gbuffer_mapping"] = result["gbuffer_mapping_status"]
        _promote_gbuffer_mask_evidence(data, result["gbuffer_mapping_status"])
        data["tmuf_smoke_test"] = "passed"
        if isinstance(data.get("proof_gate"), dict):
            data["proof_gate"]["calibration_stock_diffuse"] = "passed"
        data["tmuf_smoke_evidence"] = {
            "report": smoke_report_path.as_posix(),
            "screenshots": result["screenshots"],
            "screenshot_evidence": result["screenshot_evidence"],
            "tester": result["tester"],
            "tmuf_build": result["tmuf_build"],
            "test_date_local": result["test_date_local"],
        }
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        updated.append(path)
    return updated


def _promote_gbuffer_mask_evidence(data: dict[str, Any], gbuffer_mapping_status: str) -> None:
    if gbuffer_mapping_status != "proven_by_tmuf_smoke":
        return
    mask_evidence = data.get("mask_evidence")
    if not isinstance(mask_evidence, dict):
        return
    for entry in mask_evidence.values():
        if (
            isinstance(entry, dict)
            and entry.get("evidence_status") == "experimental_until_tmuf_smoke"
        ):
            entry["evidence_status"] = "proven_by_tmuf_smoke"
