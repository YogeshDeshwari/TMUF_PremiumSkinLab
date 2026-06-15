from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.evidence.skin_dirs import DEFAULT_REPORT as DEFAULT_SKIN_DIR_REPORT
from src.evidence.smoke_gate import validate_install_receipt_file
from src.evidence.smoke_kit import DEFAULT_KIT_DIR, validate_smoke_kit


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_READINESS_PATH = ROOT / "out" / "proof" / "tmuf_smoke_readiness.json"
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


def _install_discovered_command(candidate: dict[str, Any] | None) -> str:
    command = "python3 recipes/prepare_tmuf_smoke_kit.py --install-discovered"
    if candidate:
        search_root = str(candidate.get("search_root", "")).strip()
        if search_root:
            command += f" --search-root {search_root}"
    return command


def build_smoke_readiness(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    kit_dir = _relative_root_path(root, DEFAULT_KIT_DIR)
    kit = validate_smoke_kit(kit_dir)
    skin_dirs = _load_skin_dirs(root)
    receipt = _install_receipt_status(root)
    candidates = skin_dirs["candidates"]
    selected_candidate = candidates[0] if len(candidates) == 1 else None

    commands = _base_commands(root)
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
        "install_receipt": receipt,
        "next_actions": next_actions,
        "commands": commands,
        "proof_boundary": "This readiness report guides manual smoke setup only; it does not prove TMUF/TMNF load or GBuffer mapping.",
    }


def write_smoke_readiness(path: Path = DEFAULT_READINESS_PATH, root: Path = ROOT) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_smoke_readiness(root), indent=2, sort_keys=True) + "\n")
    return path
