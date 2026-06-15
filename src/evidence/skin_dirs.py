from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "out" / "proof" / "tmuf_skin_dirs.json"
DEFAULT_USER_DATA_ROOTS = [
    Path.home() / "Documents" / "TrackMania",
]
DEFAULT_SEARCH_ROOTS = [
    *DEFAULT_USER_DATA_ROOTS,
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
ROUTE_PRIORITY = {
    "skins_vehicles_stadiumcar": 0,
    "skins_models_stadiumcar": 1,
    "gamedata_skins_vehicles_stadiumcar": 2,
}


def _route_sort_key(item: tuple[tuple[str, ...], str]) -> tuple[int, str]:
    suffix, route = item
    return (ROUTE_PRIORITY.get(route, 99), "/".join(suffix))


def route_for_stadiumcar_skin_dir(path: Path) -> str | None:
    parts = path.parts
    for suffix, route in sorted(KNOWN_SUFFIXES.items(), key=lambda item: len(item[0]), reverse=True):
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
    root_exists = Path(root).exists()
    documents_trackmania_root = Path(root).name == "TrackMania" and Path(root).parent.name == "Documents"
    return {
        "path": path.as_posix(),
        "target_root": Path(root).as_posix(),
        "root_exists": root_exists,
        "root_parent_exists": Path(root).parent.exists(),
        "suffix": "/".join(suffix),
        "route": route,
        "exists": path.exists(),
        "requires_manual_creation": not path.exists(),
        "requires_root_creation": not root_exists,
        "preferred_suffix": route == "skins_vehicles_stadiumcar",
        "recommended_first_try": documents_trackmania_root and route == "skins_vehicles_stadiumcar",
        "status": "existing_candidate_route" if path.exists() else "manual_target_hint_not_tmuf_proof",
        "does_not_prove_tmuf_smoke": True,
        "safe_use": "Create only after confirming this root is the intended TMUF/TMNF user-data or install-data folder.",
        "evidence_boundary": "Install path hint only; not proof that TMUF/TMNF will load the skin.",
    }


def _can_suggest_creation_root(root: Path) -> bool:
    root = Path(root)
    if root.exists() and root.is_dir():
        return True
    return root.name == "TrackMania" and root.parent.name == "Documents" and root.parent.exists()


def suggest_manual_creation_targets(roots: list[Path]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for root in [Path(item) for item in roots]:
        if not _can_suggest_creation_root(root):
            continue
        for suffix, route in sorted(KNOWN_SUFFIXES.items(), key=_route_sort_key):
            targets.append(_manual_creation_target(root, suffix, route))
    return targets


def create_stadiumcar_skin_dir(path: Path) -> dict[str, Any]:
    target = Path(path)
    route = route_for_stadiumcar_skin_dir(target)
    if route is None:
        raise ValueError(f"Target is not a recognized StadiumCar skin directory path: {target}")
    if target.exists() and not target.is_dir():
        raise NotADirectoryError(target)

    created = not target.exists()
    target.mkdir(parents=True, exist_ok=True)
    quoted = shlex.quote(target.as_posix())
    return {
        "schema": "tmuf_premium_skin_lab.stadiumcar_skin_dir_create.v1",
        "status": "directory_ready_not_tested",
        "path": target.as_posix(),
        "route": route,
        "created": created,
        "does_not_prove_tmuf_smoke": True,
        "safe_use": "This only prepares a recognized StadiumCar skin folder; it does not prove TMUF/TMNF loads skins from this path.",
        "next_preflight_command": f"python3 recipes/smoke_readiness.py --install-target {quoted} --write --write-command-packet",
        "next_install_command": f"python3 recipes/prepare_tmuf_smoke_kit.py --install-skins-dir {quoted}",
    }


def _relative_depth(path: Path, root: Path) -> int:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return len(path.parts)
    return 0 if relative == Path(".") else len(relative.parts)


def _iter_stadiumcar_dirs(root: Path, max_depth: int | None) -> list[Path]:
    if not root.exists():
        return []
    matches: list[Path] = []
    for current, dirs, _files in os.walk(root):
        current_path = Path(current)
        depth = _relative_depth(current_path, root)
        if current_path.name == "StadiumCar":
            matches.append(current_path)
        if max_depth is not None and depth >= max_depth:
            dirs[:] = []
    return matches


def find_stadiumcar_skin_dirs(
    roots: list[Path] | None = None,
    *,
    max_depth: int | None = None,
) -> list[dict[str, Any]]:
    search_roots = [Path(root) for root in (roots if roots is not None else DEFAULT_SEARCH_ROOTS)]
    seen: set[Path] = set()
    candidates: list[dict[str, Any]] = []
    for root in search_roots:
        for path in _iter_stadiumcar_dirs(root, max_depth):
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
    max_depth: int | None = None,
) -> dict[str, Any]:
    search_roots = [Path(root) for root in (roots if roots is not None else DEFAULT_SEARCH_ROOTS)]
    candidates = find_stadiumcar_skin_dirs(search_roots, max_depth=max_depth)
    manual_creation_targets = suggest_manual_creation_targets(search_roots) if include_creation_targets else []
    recommended_creation_target = None
    if not candidates and manual_creation_targets:
        recommended_creation_target = next(
            (target for target in manual_creation_targets if target.get("recommended_first_try")),
            manual_creation_targets[0],
        )
    return {
        "schema_version": 1,
        "status": "candidates_found" if candidates else "no_candidates_found",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "manual_creation_targets": manual_creation_targets,
        "recommended_creation_target": recommended_creation_target,
        "default_user_data_roots": [path.as_posix() for path in DEFAULT_USER_DATA_ROOTS],
        "install_path_evidence_doc": "docs/tmuf_install_paths.md",
        "scan_boundary": {
            "max_depth": max_depth,
            "bounded_by_max_depth": max_depth is not None,
            "does_not_prove_tmuf_smoke": True,
        },
        "does_not_prove_tmuf_smoke": True,
        "safe_use": "Use a listed path only as an explicit install target; finding or planning a directory does not prove TMUF load.",
    }


def write_skin_dir_report(
    path: Path = DEFAULT_REPORT,
    roots: list[Path] | None = None,
    *,
    include_creation_targets: bool = False,
    max_depth: int | None = None,
) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            build_skin_dir_report(
                roots,
                include_creation_targets=include_creation_targets,
                max_depth=max_depth,
            ),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return path
