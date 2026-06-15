from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.evidence.smoke_gate import (
    CALIBRATION_ARTIFACT,
    REQUIRED_OBSERVATIONS,
    REQUIRED_SCREENSHOT_ROLES,
    evaluate_smoke_report,
    fingerprint_install_receipt_file,
    fingerprint_screenshot_file,
    validate_install_receipt_file,
    validate_screenshot_file,
)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "out" / "proof" / "calibration_tmuf_smoke.json"


def _require_nonempty(name: str, value: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _report_path(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    base = base_dir.resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return resolved.as_posix()


def _copy_install_receipt_evidence(receipt_path: Path, output_path: Path, base_dir: Path) -> tuple[str, dict[str, object]]:
    source = Path(receipt_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    validation = validate_install_receipt_file(source, base_dir=base_dir)
    if not validation["valid"]:
        raise ValueError(f"Install receipt is not valid: {validation['errors']}")

    destination = output_path.parent / "calibration_install_receipt.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    report_path = _report_path(destination, base_dir)
    return report_path, fingerprint_install_receipt_file(destination, base_dir=base_dir)


def _confirmed_observation_map(
    *,
    all_required_observations_passed: bool,
    confirmed_observations: list[str] | None,
) -> tuple[dict[str, bool], str]:
    if all_required_observations_passed:
        return {name: True for name in REQUIRED_OBSERVATIONS}, "all_required_flag"

    confirmed = list(confirmed_observations or [])
    unknown = sorted(set(confirmed) - set(REQUIRED_OBSERVATIONS))
    if unknown:
        raise ValueError(f"Unknown calibration observations: {unknown}")

    confirmed_set = set(confirmed)
    missing = [name for name in REQUIRED_OBSERVATIONS if name not in confirmed_set]
    if missing:
        raise ValueError(f"Cannot record passed smoke evidence until all required observations are confirmed: {missing}")

    return {name: True for name in REQUIRED_OBSERVATIONS}, "explicit"


def record_calibration_smoke_report(
    *,
    output_path: Path = DEFAULT_OUTPUT,
    tester: str,
    tmuf_build: str,
    test_date_local: str,
    screenshot_roles: dict[str, Path],
    all_required_observations_passed: bool,
    confirmed_observations: list[str] | None = None,
    install_receipt: Path | None = None,
    notes: str = "",
    base_dir: Path = ROOT,
) -> Path:
    observations, observation_confirmation_mode = _confirmed_observation_map(
        all_required_observations_passed=all_required_observations_passed,
        confirmed_observations=confirmed_observations,
    )
    screenshot_roles = dict(screenshot_roles or {})
    unknown_roles = sorted(set(screenshot_roles) - set(REQUIRED_SCREENSHOT_ROLES))
    if unknown_roles:
        raise ValueError(f"Unknown screenshot roles: {unknown_roles}")
    missing_roles = [role for role in REQUIRED_SCREENSHOT_ROLES if role not in screenshot_roles]
    if missing_roles:
        raise ValueError(f"Missing required screenshot roles: {missing_roles}")

    base = Path(base_dir)
    output = Path(output_path)
    screenshot_dir = base / "out" / "proof" / "tmuf_smoke_screenshots"
    output.parent.mkdir(parents=True, exist_ok=True)

    copied_screenshots: list[str] = []
    copied_roles: dict[str, str] = {}
    screenshot_evidence: dict[str, dict[str, object]] = {}
    for role in REQUIRED_SCREENSHOT_ROLES:
        source_path = screenshot_roles[role]
        source = Path(source_path)
        if not source.is_file():
            raise FileNotFoundError(source)
        validation = validate_screenshot_file(source)
        if not validation["readable"]:
            raise ValueError(f"Screenshot must be a readable image: {source}")
        if not validation["nonblank"]:
            raise ValueError(f"Screenshot must be nonblank: {source}")
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        destination = screenshot_dir / source.name
        shutil.copy2(source, destination)
        report_path = _report_path(destination, base)
        copied_screenshots.append(report_path)
        copied_roles[role] = report_path
        screenshot_evidence[report_path] = fingerprint_screenshot_file(destination)

    install_receipt_report_path = ""
    install_receipt_evidence: dict[str, object] = {}
    if install_receipt is not None:
        install_receipt_report_path, install_receipt_evidence = _copy_install_receipt_evidence(
            Path(install_receipt),
            output,
            base,
        )

    data = {
        "schema_version": 1,
        "artifact": CALIBRATION_ARTIFACT,
        "route": "stock_diffuse_only",
        "status": "passed",
        "tester": _require_nonempty("tester", tester),
        "tmuf_build": _require_nonempty("tmuf_build", tmuf_build),
        "test_date_local": _require_nonempty("test_date_local", test_date_local),
        "screenshots": copied_screenshots,
        "screenshot_roles": copied_roles,
        "screenshot_evidence": screenshot_evidence,
        "install_receipt": install_receipt_report_path,
        "install_receipt_evidence": install_receipt_evidence,
        "observations": observations,
        "observation_confirmation_mode": observation_confirmation_mode,
        "notes": notes,
        "recorded_by": "recipes/record_tmuf_smoke.py",
    }

    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    result = evaluate_smoke_report(output, base_dir=base)
    if not result["passed"]:
        output.unlink(missing_ok=True)
        raise ValueError(f"Recorded smoke report did not evaluate as passed: {result}")
    return output
