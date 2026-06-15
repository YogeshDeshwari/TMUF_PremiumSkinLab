from __future__ import annotations

import json
import shutil
from hashlib import sha256
from pathlib import Path
from typing import Any

from src.evidence.skin_dirs import build_skin_dir_report, route_for_stadiumcar_skin_dir
from src.stock_diffuse.premium import CANDIDATE_NAMES


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RECEIPT = ROOT / "out" / "proof" / "premium_review_install_receipt.json"


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _validate_install_dir(skins_dir: Path) -> str:
    skins_dir = Path(skins_dir)
    if not skins_dir.exists():
        raise FileNotFoundError(skins_dir)
    if not skins_dir.is_dir():
        raise NotADirectoryError(skins_dir)
    route = route_for_stadiumcar_skin_dir(skins_dir)
    if route is None:
        raise ValueError(f"Install target is not a recognized StadiumCar skin directory: {skins_dir}")
    return route


def _skin_entry(name: str, source: Path, destination: Path) -> dict[str, Any]:
    return {
        "name": name,
        "package_route": "stock_diffuse_only",
        "tmuf_smoke_test": "not_run",
        "source_skin": str(source),
        "installed_skin": str(destination),
        "sha256": _digest(destination),
        "source_sha256": _digest(source),
        "size_bytes": destination.stat().st_size,
        "does_not_prove_tmuf_smoke": True,
    }


def install_premium_review_skins(
    skins_dir: Path,
    *,
    root: Path = ROOT,
    candidate_names: list[str] | tuple[str, ...] = CANDIDATE_NAMES,
) -> dict[str, Any]:
    skins_dir = Path(skins_dir)
    route = _validate_install_dir(skins_dir)
    installed: list[dict[str, Any]] = []
    for name in candidate_names:
        source = Path(root) / "out" / "skins" / f"{name}.zip"
        destination = skins_dir / f"{name}.zip"
        _copy_file(source, destination)
        installed.append(_skin_entry(name, source, destination))

    return {
        "status": "installed_for_visual_review_not_tested",
        "selection_mode": "explicit_install_target",
        "install_target": str(skins_dir),
        "route": route,
        "candidate_count": len(installed),
        "installed_skins": installed,
        "calibration_gate_status": "pending_tmuf_smoke",
        "proof_boundary": (
            "This receipt proves file copy/hash only. It does not prove TMUF/TMNF load, "
            "stock GBuffer mapping, or visual acceptance."
        ),
        "does_not_prove_tmuf_smoke": True,
        "next_required_evidence": [
            "run_tmuf_calibration_smoke_test",
            "record_tmuf_smoke_evidence",
            "evaluate_then_apply_tmuf_smoke_gate",
            "manual_visual_feedback_on_premium_candidates",
        ],
    }


def install_discovered_premium_review_skins(
    roots: list[Path] | None = None,
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    discovery = build_skin_dir_report(roots)
    candidates = discovery["candidates"]
    if len(candidates) != 1:
        raise ValueError(
            "Discovered premium review install requires exactly one recognized StadiumCar skin directory; "
            f"found {len(candidates)}"
        )
    result = install_premium_review_skins(Path(candidates[0]["path"]), root=root)
    result["selection_mode"] = "single_discovered_candidate"
    result["selected_candidate"] = candidates[0]
    result["discovery"] = discovery
    return result


def write_premium_review_receipt(
    install_result: dict[str, Any],
    path: Path = DEFAULT_RECEIPT,
) -> Path:
    path = Path(path)
    data = {
        "schema": "tmuf_premium_skin_lab.premium_review_install_receipt.v1",
        **install_result,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return path
