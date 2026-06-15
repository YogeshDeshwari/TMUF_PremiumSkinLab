from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS, REQUIRED_SCREENSHOT_ROLES, validate_install_receipt_file
from src.evidence.smoke_kit import DEFAULT_KIT_DIR
from src.evidence.smoke_record import DEFAULT_OUTPUT


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SESSION_DIR = ROOT / "out" / "proof" / "tmuf_smoke_session"
DEFAULT_INSTALL_RECEIPT = DEFAULT_KIT_DIR / "proof" / "calibration_install_receipt.json"
SCREENSHOT_FILENAMES = {
    "front": "tmuf_calibration_front.png",
    "side": "tmuf_calibration_side.png",
    "rear": "tmuf_calibration_rear.png",
    "top": "tmuf_calibration_top.png",
}


def _relative(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    base = base_dir.resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return resolved.as_posix()


def _quote_command(parts: list[str | Path]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def _record_command(
    *,
    output_path: Path,
    install_receipt: Path,
    screenshot_paths: dict[str, Path],
) -> str:
    parts: list[str | Path] = [
        "python3",
        "recipes/record_tmuf_smoke.py",
        "--tester",
        "manual tester",
        "--tmuf-build",
        "TMUF local install",
        "--test-date-local",
        "YYYY-MM-DD",
        "--install-receipt",
        install_receipt,
    ]
    for role in REQUIRED_SCREENSHOT_ROLES:
        parts.extend(["--screenshot-role", f"{role}={screenshot_paths[role]}"])
    parts.append("--all-required-observations-passed")
    parts.extend(["--output", output_path])
    return _quote_command(parts)


def _readme_text(manifest: dict[str, Any]) -> str:
    lines = [
        "# TMUF Smoke Evidence Session",
        "",
        "This folder is a capture scaffold only. It does not prove TMUF/TMNF",
        "loaded the calibration skin and it does not prove GBuffer mapping.",
        "",
        "Save real TMUF/TMNF screenshots at these exact paths:",
    ]
    for slot in manifest["screenshot_slots"]:
        lines.append(f"- {slot['role']}: `{slot['path']}`")
    lines.extend(
        [
            "",
            "Before recording evidence, verify every observation in TMUF/TMNF:",
        ]
    )
    lines.extend(f"- {observation}" for observation in REQUIRED_OBSERVATIONS)
    lines.extend(
        [
            "",
            "After the screenshots exist, run:",
            "",
            "```bash",
            manifest["record_command"],
            "```",
            "",
            "The command will fail if any screenshot is missing, unreadable, or blank.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_smoke_session(
    session_dir: Path = DEFAULT_SESSION_DIR,
    *,
    base_dir: Path = ROOT,
    install_receipt: Path = DEFAULT_INSTALL_RECEIPT,
    output_path: Path = DEFAULT_OUTPUT,
) -> dict[str, Any]:
    base = Path(base_dir)
    session = Path(session_dir)
    screenshots_dir = session / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    screenshot_paths = {
        role: screenshots_dir / SCREENSHOT_FILENAMES[role]
        for role in REQUIRED_SCREENSHOT_ROLES
    }
    command = _record_command(
        output_path=Path(output_path),
        install_receipt=Path(install_receipt),
        screenshot_paths=screenshot_paths,
    )
    receipt_exists = Path(install_receipt).is_file()
    receipt_validation = (
        validate_install_receipt_file(Path(install_receipt), base_dir=base)
        if receipt_exists
        else {
            "readable": False,
            "valid": False,
            "errors": ["missing_install_receipt"],
        }
    )
    manifest = {
        "schema": "tmuf_premium_skin_lab.smoke_session.v1",
        "status": "awaiting_tmuf_screenshots",
        "does_not_prove_tmuf_smoke": True,
        "base_dir": str(base),
        "session_dir": str(session),
        "screenshots_dir": str(screenshots_dir),
        "output_report": _relative(Path(output_path), base),
        "install_receipt": str(install_receipt),
        "install_receipt_valid": receipt_validation["valid"],
        "install_receipt_errors": receipt_validation["errors"],
        "required_observations": REQUIRED_OBSERVATIONS,
        "screenshot_slots": [
            {
                "role": role,
                "path": str(screenshot_paths[role]),
                "exists": screenshot_paths[role].exists(),
                "required": True,
            }
            for role in REQUIRED_SCREENSHOT_ROLES
        ],
        "record_command": command,
        "record_command_file": str(session / "record_tmuf_smoke_command.txt"),
        "readme": str(session / "README_tmuf_smoke_session.md"),
        "proof_boundary": (
            "This session scaffold only prepares screenshot paths and a record command; "
            "it is not TMUF smoke evidence."
        ),
    }
    (session / "session_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (session / "record_tmuf_smoke_command.txt").write_text(command + "\n")
    (session / "README_tmuf_smoke_session.md").write_text(_readme_text(manifest))
    return manifest
