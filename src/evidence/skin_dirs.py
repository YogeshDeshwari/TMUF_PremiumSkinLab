from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "out" / "proof" / "tmuf_skin_dirs.json"
DEFAULT_SEARCH_ROOTS = [
    Path.home() / "Documents",
    Path.home() / "Library" / "Application Support" / "Steam",
    Path.home() / "Library" / "Application Support" / "CrossOver",
    Path.home() / ".wine",
    Path("/Applications"),
    Path.home() / "Applications",
]


KNOWN_SUFFIXES = {
    ("Skins", "Vehicles", "StadiumCar"): "skins_vehicles_stadiumcar",
    ("GameData", "Skins", "Vehicles", "StadiumCar"): "gamedata_skins_vehicles_stadiumcar",
    ("Skins", "Models", "StadiumCar"): "skins_models_stadiumcar",
}


def route_for_stadiumcar_skin_dir(path: Path) -> str | None:
    parts = path.parts
    for suffix, route in KNOWN_SUFFIXES.items():
        if len(parts) >= len(suffix) and tuple(parts[-len(suffix) :]) == suffix:
            return route
    return None


def _candidate(path: Path, root: Path, route: str) -> dict[str, Any]:
    zips = sorted(child for child in path.iterdir() if child.is_file() and child.suffix.lower() == ".zip")
    return {
        "path": path.as_posix(),
        "search_root": root.as_posix(),
        "route": route,
        "confidence": "high",
        "existing_zip_count": len(zips),
        "does_not_prove_tmuf_smoke": True,
    }


def _manual_creation_target(root: Path, suffix: tuple[str, ...], route: str) -> dict[str, Any]:
    path = Path(root).joinpath(*suffix)
    return {
        "path": path.as_posix(),
        "target_root": Path(root).as_posix(),
        "suffix": "/".join(suffix),
        "route": route,
        "exists": path.exists(),
        "requires_manual_creation": not path.exists(),
        "status": "existing_candidate_route" if path.exists() else "manual_target_hint_not_tmuf_proof",
        "does_not_prove_tmuf_smoke": True,
        "safe_use": "Create only after confirming this root is the intended TMUF/TMNF user-data or install-data folder.",
    }


def suggest_manual_creation_targets(roots: list[Path]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for root in [Path(item) for item in roots]:
        if not root.exists() or not root.is_dir():
            continue
        for suffix, route in sorted(KNOWN_SUFFIXES.items(), key=lambda item: item[1]):
            targets.append(_manual_creation_target(root, suffix, route))
    return targets


def find_stadiumcar_skin_dirs(roots: list[Path] | None = None) -> list[dict[str, Any]]:
    search_roots = [Path(root) for root in (roots if roots is not None else DEFAULT_SEARCH_ROOTS)]
    seen: set[Path] = set()
    candidates: list[dict[str, Any]] = []
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("StadiumCar"):
            if not path.is_dir():
                continue
            route = route_for_stadiumcar_skin_dir(path)
            if route is None:
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            candidates.append(_candidate(path, root, route))
    return sorted(candidates, key=lambda item: item["path"])


def build_skin_dir_report(
    roots: list[Path] | None = None,
    *,
    include_creation_targets: bool = False,
) -> dict[str, Any]:
    search_roots = [Path(root) for root in (roots if roots is not None else DEFAULT_SEARCH_ROOTS)]
    candidates = find_stadiumcar_skin_dirs(search_roots)
    manual_creation_targets = suggest_manual_creation_targets(search_roots) if include_creation_targets else []
    return {
        "schema_version": 1,
        "status": "candidates_found" if candidates else "no_candidates_found",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "manual_creation_targets": manual_creation_targets,
        "does_not_prove_tmuf_smoke": True,
        "safe_use": "Use a listed path only as an explicit install target; finding or planning a directory does not prove TMUF load.",
    }


def write_skin_dir_report(
    path: Path = DEFAULT_REPORT,
    roots: list[Path] | None = None,
    *,
    include_creation_targets: bool = False,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            build_skin_dir_report(roots, include_creation_targets=include_creation_targets),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return path
