from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_entry(path: Path) -> dict[str, Any]:
    path = Path(path)
    rel = path.relative_to(ROOT).as_posix()
    return {
        "path": rel,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def stock_output_artifacts(zip_path: Path, atlas_path: Path, projection_path: Path) -> dict[str, dict[str, Any]]:
    return {
        "skin_zip": artifact_entry(zip_path),
        "atlas_preview": artifact_entry(atlas_path),
        "projected_preview": artifact_entry(projection_path),
    }
