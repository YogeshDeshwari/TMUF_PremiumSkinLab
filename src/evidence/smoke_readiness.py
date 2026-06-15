from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any

from src.evidence.skin_dirs import (
    DEFAULT_REPORT as DEFAULT_SKIN_DIR_REPORT,
    KNOWN_SUFFIXES,
    route_for_stadiumcar_skin_dir,
)
from src.evidence.smoke_gate import validate_install_receipt_file
from src.evidence.smoke_kit import CALIBRATION_SKIN, DEFAULT_KIT_DIR, validate_smoke_kit


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_READINESS_PATH = ROOT / "out" / "proof" / "tmuf_smoke_readiness.json"
DEFAULT_COMMAND_PACKET = ROOT / "out" / "proof" / "tmuf_manual_smoke_commands.txt"
DEFAULT_INSTALL_RECEIPT = DEFAULT_KIT_DIR / "proof" / "calibration_install_receipt.json"


def _relative_root_path(root: Path, repo_path: Path) -> Path:
    return root / repo_path.relative_to(ROOT)


def _load_skin_dirs(root: Path) -> dict[str, Any]:
    report_path = _relative_root_path(root, DEFAULT_SKIN_DIR_REPORT)
    if not report_path.exists():
        return {
            "exists": False,
            "status": "not_scanned",
            "candidate_count": 0,
            "candidates": [],
            "report": str(report_path),
            "does_not_prove_tmuf_smoke": True,
        }
    data = json.loads(report_path.read_text())
    return {
        "exists": True,
        "status": data.get("status", "unknown"),
        "candidate_count": data.get("candidate_count", 0),
        "candidates": data.get("candidates", []),
        "report": str(report_path),
        "does_not_prove_tmuf_smoke": data.get("does_not_prove_tmuf_smoke", True),
    }


def _install_receipt_status(root: Path) -> dict[str, Any]:
    receipt_path = _relative_root_path(root, DEFAULT_INSTALL_RECEIPT)
    if not receipt_path.exists():
        return {
            "exists": False,
            "valid": False,
            "path": str(receipt_path),
            "errors": ["missing_install_receipt"],
            "does_not_prove_tmuf_smoke": True,
        }
    validation = validate_install_receipt_file(receipt_path, base_dir=root)
    return {
        "exists": True,
        "valid": validation["valid"],
        "path": str(receipt_path),
        "errors": validation["errors"],
        "route": validation.get("route"),
        "installed_skin": validation.get("installed_skin"),
        "installed_sha256": validation.get("installed_sha256"),
        "receipt_sha256": validation.get("receipt_sha256"),
        "does_not_prove_tmuf_smoke": True,
    }


def _base_commands(root: Path) -> dict[str, str]:
    receipt = _relative_root_path(root, DEFAULT_INSTALL_RECEIPT)
    return {
        "build_smoke_kit": "python3 recipes/prepare_tmuf_smoke_kit.py",
        "scan_skin_dirs": "python3 recipes/find_tmuf_skin_dirs.py --write",
        "scan_custom_root": (
            "python3 recipes/find_tmuf_skin_dirs.py "
            "--root /absolute/path/to/TrackMania-or-Wine-prefix --write --json"
        ),
        "preflight_explicit": (
            "python3 recipes/smoke_readiness.py "
            "--install-target /absolute/path/to/StadiumCar --write --write-command-packet"
        ),
        "install_explicit": "python3 recipes/prepare_tmuf_smoke_kit.py --install-skins-dir /absolute/path/to/StadiumCar",
        "record_smoke": (
            "python3 recipes/record_tmuf_smoke.py "
            "--tester \"manual tester\" "
            "--tmuf-build \"TMUF local install\" "
            "--test-date-local YYYY-MM-DD "
            f"--install-receipt {receipt} "
            "--screenshot-role front=/absolute/path/to/tmuf_front.png "
            "--screenshot-role side=/absolute/path/to/tmuf_side.png "
            "--screenshot-role rear=/absolute/path/to/tmuf_rear.png "
            "--screenshot-role top=/absolute/path/to/tmuf_top.png "
            "--all-required-observations-passed"
        ),
        "evaluate": "python3 recipes/tmuf_smoke_gate.py --evaluate out/proof/calibration_tmuf_smoke.json",
        "apply_after_pass_only": "python3 recipes/tmuf_smoke_gate.py --apply out/proof/calibration_tmuf_smoke.json",
    }


def _preflight_install_target(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    target = Path(path)
    errors: list[str] = []
    if not target.exists():
        errors.append("target_missing")
    if target.exists() and not target.is_dir():
        errors.append("target_not_directory")
    route = route_for_stadiumcar_skin_dir(target)
    if route is None:
        errors.append("unrecognized_stadiumcar_route")

    existing_zip_count = 0
    calibration_present = False
    calibration_matches_source = False
    writable = False
    if target.is_dir():
        existing_zip_count = len([child for child in target.iterdir() if child.is_file() and child.suffix.lower() == ".zip"])
        calibration_path = target / "calibration_stock_diffuse.zip"
        calibration_present = calibration_path.exists()
        calibration_matches_source = (
            calibration_path.is_file()
            and CALIBRATION_SKIN.exists()
            and calibration_path.read_bytes() == CALIBRATION_SKIN.read_bytes()
        )
        writable = os.access(target, os.W_OK)
        if not writable:
            errors.append("target_not_writable")

    return {
        "path": str(target),
        "exists": target.exists(),
        "is_dir": target.is_dir(),
        "route": route,
        "writable": writable,
        "existing_zip_count": existing_zip_count,
        "calibration_present": calibration_present,
        "calibration_matches_source": calibration_matches_source,
        "valid": not errors,
        "errors": errors,
        "does_not_prove_tmuf_smoke": True,
    }


def _install_discovered_command(candidate: dict[str, Any] | None) -> str:
    command = "python3 recipes/prepare_tmuf_smoke_kit.py --install-discovered"
    if candidate:
        search_root = str(candidate.get("search_root", "")).strip()
        if search_root:
            command += f" --search-root {search_root}"
    return command


def build_smoke_readiness(root: Path = ROOT, *, install_target: Path | None = None) -> dict[str, Any]:
    root = Path(root)
    kit_dir = _relative_root_path(root, DEFAULT_KIT_DIR)
    kit = validate_smoke_kit(kit_dir)
    skin_dirs = _load_skin_dirs(root)
    receipt = _install_receipt_status(root)
    target_preflight = _preflight_install_target(install_target)
    candidates = skin_dirs["candidates"]
    selected_candidate = candidates[0] if len(candidates) == 1 else None

    commands = _base_commands(root)
    if target_preflight is not None:
        commands["install_explicit"] = (
            "python3 recipes/prepare_tmuf_smoke_kit.py "
            f"--install-skins-dir {shlex.quote(target_preflight['path'])}"
        )
        commands["preflight_explicit"] = (
            "python3 recipes/smoke_readiness.py "
            f"--install-target {shlex.quote(target_preflight['path'])} "
            "--write --write-command-packet"
        )
    commands["install_discovered"] = _install_discovered_command(selected_candidate)

    if not kit["fresh"]:
        status = "needs_fresh_smoke_kit"
        next_actions = ["build_smoke_kit"]
    elif receipt["valid"]:
        status = "ready_to_run_tmuf_smoke"
        next_actions = [
            "run_tmuf_calibration_smoke_test",
            "record_tmuf_smoke_evidence",
            "evaluate_then_apply_tmuf_smoke_gate",
        ]
    elif target_preflight is not None and not target_preflight["valid"]:
        status = "explicit_install_target_invalid"
        next_actions = ["fix_explicit_install_target", "rerun_smoke_readiness"]
    elif target_preflight is not None:
        status = "ready_for_explicit_install"
        next_actions = ["install_with_explicit_target", "run_tmuf_calibration_smoke_test"]
    elif skin_dirs["candidate_count"] == 0:
        status = "needs_explicit_stadiumcar_dir"
        next_actions = ["choose_or_create_tmuf_stadiumcar_skin_dir", "install_with_explicit_target"]
    elif skin_dirs["candidate_count"] == 1:
        status = "ready_for_guarded_discovered_install"
        next_actions = ["install_with_guarded_discovery", "run_tmuf_calibration_smoke_test"]
    else:
        status = "needs_explicit_choice_from_candidates"
        next_actions = ["choose_one_stadiumcar_candidate", "install_with_explicit_target"]

    return {
        "schema": "tmuf_premium_skin_lab.smoke_readiness.v1",
        "status": status,
        "does_not_prove_tmuf_smoke": True,
        "root": str(root),
        "smoke_kit": {
            "exists": kit["exists"],
            "fresh": kit["fresh"],
            "freshness_status": kit["status"],
            "manifest_status": kit["manifest_status"],
            "missing_files": kit["missing_files"],
            "stale_files": kit["stale_files"],
            "zip_missing_or_stale": kit["zip_missing_or_stale"],
        },
        "skin_dirs": skin_dirs,
        "selected_candidate": selected_candidate,
        "install_target_preflight": target_preflight,
        "install_receipt": receipt,
        "recognized_install_routes": [
            {"suffix": "/".join(suffix), "route": route}
            for suffix, route in sorted(KNOWN_SUFFIXES.items(), key=lambda item: item[1])
        ],
        "next_actions": next_actions,
        "commands": commands,
        "proof_boundary": "This readiness report guides manual smoke setup only; it does not prove TMUF/TMNF load or GBuffer mapping.",
    }


def write_smoke_readiness(
    path: Path = DEFAULT_READINESS_PATH,
    root: Path = ROOT,
    *,
    install_target: Path | None = None,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(build_smoke_readiness(root, install_target=install_target), indent=2, sort_keys=True) + "\n"
    )
    return path


def format_smoke_command_packet(readiness: dict[str, Any]) -> str:
    lines = [
        "TMUF PremiumSkinLab Manual Smoke Command Packet",
        f"status={readiness['status']}",
        "does_not_prove_tmuf_smoke=true",
        f"proof_boundary={readiness['proof_boundary']}",
        "",
        "Next actions:",
    ]
    lines.extend(f"- {action}" for action in readiness["next_actions"])
    target_preflight = readiness.get("install_target_preflight")
    if target_preflight is not None:
        lines.extend(
            [
                "",
                "Install target preflight:",
                f"path={target_preflight['path']}",
                f"route={target_preflight['route']}",
                f"valid={str(target_preflight['valid']).lower()}",
                f"errors={','.join(target_preflight['errors']) if target_preflight['errors'] else 'none'}",
                "does_not_prove_tmuf_smoke=true",
            ]
        )
    lines.extend(["", "Commands:"])
    for name in [
        "build_smoke_kit",
        "scan_skin_dirs",
        "scan_custom_root",
        "preflight_explicit",
        "install_explicit",
        "install_discovered",
        "record_smoke",
        "evaluate",
        "apply_after_pass_only",
    ]:
        command = readiness["commands"].get(name)
        if command:
            lines.extend([f"{name}:", f"  {command}"])
    lines.extend(["", "Recognized StadiumCar folder suffixes:"])
    for item in readiness.get("recognized_install_routes", []):
        lines.append(f"- {item['suffix']} ({item['route']})")
    lines.extend(
        [
            "",
            "Rules:",
            "- Replace placeholder paths before recording smoke evidence.",
            "- Do not run apply until evaluate passes.",
            "- This packet is a setup aid only; it is not TMUF smoke evidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_smoke_command_packet(
    path: Path = DEFAULT_COMMAND_PACKET,
    root: Path = ROOT,
    *,
    install_target: Path | None = None,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_smoke_command_packet(build_smoke_readiness(root, install_target=install_target)))
    return path
