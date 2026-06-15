from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from src.evidence.smoke_gate import fingerprint_screenshot_file, validate_screenshot_file
from src.stock_diffuse.premium import CANDIDATE_NAMES


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "out" / "proof" / "premium_visual_review.json"
REQUIRED_PREMIUM_REVIEW_ROLES = ["front", "side", "rear", "top"]
VALID_VERDICTS = {"accepted", "needs_iteration", "rejected"}


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


def _resolve_evidence_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base_dir / path


def _copy_review_screenshots(
    *,
    skin_name: str,
    screenshot_roles: dict[str, Path],
    base_dir: Path,
) -> tuple[list[str], dict[str, str], dict[str, dict[str, object]]]:
    screenshot_roles = dict(screenshot_roles or {})
    unknown_roles = sorted(set(screenshot_roles) - set(REQUIRED_PREMIUM_REVIEW_ROLES))
    if unknown_roles:
        raise ValueError(f"Unknown screenshot roles: {unknown_roles}")
    missing_roles = [role for role in REQUIRED_PREMIUM_REVIEW_ROLES if role not in screenshot_roles]
    if missing_roles:
        raise ValueError(f"Missing required screenshot roles: {missing_roles}")

    screenshot_dir = base_dir / "out" / "proof" / "premium_visual_review" / skin_name
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    copied_roles: dict[str, str] = {}
    evidence: dict[str, dict[str, object]] = {}
    for role in REQUIRED_PREMIUM_REVIEW_ROLES:
        source = Path(screenshot_roles[role])
        if not source.is_file():
            raise FileNotFoundError(source)
        validation = validate_screenshot_file(source)
        if not validation["readable"]:
            raise ValueError(f"Screenshot must be a readable image: {source}")
        if not validation["nonblank"]:
            raise ValueError(f"Screenshot must be nonblank: {source}")
        destination = screenshot_dir / f"{role}_{source.name}"
        shutil.copy2(source, destination)
        report_path = _report_path(destination, base_dir)
        copied.append(report_path)
        copied_roles[role] = report_path
        evidence[report_path] = fingerprint_screenshot_file(destination)
    return copied, copied_roles, evidence


def record_premium_visual_review(
    *,
    skin_name: str,
    verdict: str,
    tester: str,
    tmuf_build: str,
    test_date_local: str,
    screenshot_roles: dict[str, Path],
    notes: str = "",
    output_path: Path = DEFAULT_OUTPUT,
    base_dir: Path = ROOT,
) -> Path:
    skin = _require_nonempty("skin_name", skin_name)
    if skin not in CANDIDATE_NAMES:
        raise ValueError(f"Unknown premium candidate: {skin}")
    clean_verdict = _require_nonempty("verdict", verdict)
    if clean_verdict not in VALID_VERDICTS:
        raise ValueError(f"Unknown review verdict: {clean_verdict}")

    base = Path(base_dir)
    output = Path(output_path)
    screenshots, copied_roles, screenshot_evidence = _copy_review_screenshots(
        skin_name=skin,
        screenshot_roles=screenshot_roles,
        base_dir=base,
    )

    data = {
        "schema": "tmuf_premium_skin_lab.premium_visual_review.v1",
        "status": "visual_review_recorded",
        "skin_name": skin,
        "route": "stock_diffuse_only",
        "package_files": ["Diffuse.dds", "Icon.dds"],
        "verdict": clean_verdict,
        "tester": _require_nonempty("tester", tester),
        "tmuf_build": _require_nonempty("tmuf_build", tmuf_build),
        "test_date_local": _require_nonempty("test_date_local", test_date_local),
        "screenshots": screenshots,
        "screenshot_roles": copied_roles,
        "screenshot_evidence": screenshot_evidence,
        "notes": notes,
        "calibration_gate_status": "pending_or_separate",
        "does_not_prove_tmuf_smoke": True,
        "does_not_prove_gbuffer_mapping": True,
        "proof_boundary": (
            "This records manual visual feedback for one premium candidate. It does not prove the "
            "calibration smoke gate, GBuffer mapping, or stock route correctness."
        ),
        "recorded_by": "recipes/record_premium_visual_review.py",
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    result = evaluate_premium_visual_review(output, base_dir=base)
    if not result["valid"]:
        output.unlink(missing_ok=True)
        raise ValueError(f"Recorded premium visual review did not validate: {result}")
    return output


def evaluate_premium_visual_review(path: Path, base_dir: Path | None = None) -> dict[str, Any]:
    path = Path(path)
    data = json.loads(path.read_text())
    base = Path(base_dir) if base_dir is not None else ROOT

    missing_metadata = [
        name
        for name in ["skin_name", "verdict", "tester", "tmuf_build", "test_date_local"]
        if not str(data.get(name, "")).strip()
    ]
    unknown_skin = data.get("skin_name") not in CANDIDATE_NAMES
    unknown_verdict = data.get("verdict") not in VALID_VERDICTS

    raw_roles = data.get("screenshot_roles", {})
    if not isinstance(raw_roles, dict):
        raw_roles = {}
    screenshot_roles = {str(role): str(value) for role, value in raw_roles.items() if str(value).strip()}
    missing_screenshot_roles = [role for role in REQUIRED_PREMIUM_REVIEW_ROLES if role not in screenshot_roles]
    screenshots = [screenshot_roles[role] for role in REQUIRED_PREMIUM_REVIEW_ROLES if role in screenshot_roles]
    missing_screenshots = [item for item in screenshots if not _resolve_evidence_path(item, base).exists()]
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

    valid = (
        data.get("schema") == "tmuf_premium_skin_lab.premium_visual_review.v1"
        and data.get("status") == "visual_review_recorded"
        and not missing_metadata
        and not unknown_skin
        and not unknown_verdict
        and not missing_screenshot_roles
        and not missing_screenshots
        and not invalid_screenshots
        and not blank_screenshots
        and not missing_screenshot_fingerprints
        and not mismatched_screenshot_fingerprints
        and data.get("does_not_prove_tmuf_smoke") is True
        and data.get("does_not_prove_gbuffer_mapping") is True
    )
    return {
        "valid": valid,
        "status": "valid" if valid else "invalid",
        "skin_name": data.get("skin_name"),
        "verdict": data.get("verdict"),
        "unknown_skin": unknown_skin,
        "unknown_verdict": unknown_verdict,
        "missing_metadata": missing_metadata,
        "screenshots": screenshots,
        "screenshot_roles": screenshot_roles,
        "missing_screenshot_roles": missing_screenshot_roles,
        "missing_screenshots": missing_screenshots,
        "invalid_screenshots": invalid_screenshots,
        "blank_screenshots": blank_screenshots,
        "screenshot_validation": screenshot_validation,
        "missing_screenshot_fingerprints": missing_screenshot_fingerprints,
        "mismatched_screenshot_fingerprints": mismatched_screenshot_fingerprints,
    }
