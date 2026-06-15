from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "resources" / "evidence_manifest.json"
STOCK_DIFFUSE_INPUTS = [
    "authoritative/gbuffer/position_2048.npy",
    "authoritative/gbuffer/coverage_2048.npy",
    "authoritative/gbuffer/extents_2048.json",
    "authoritative/parts/psd_parts_labels.npy",
    "authoritative/parts/psd_parts.json",
    "authoritative/reference/official_prelight_AO.png",
]
PREMIUM_DIFFUSE_INPUTS = [
    *STOCK_DIFFUSE_INPUTS,
    "authoritative/parts/panels_high_labels.npy",
    "authoritative/parts/panels_high.json",
    "authoritative/parts/panels_fine_labels.npy",
    "authoritative/parts/panels_fine.json",
]


def load_manifest_entries() -> dict[str, dict[str, Any]]:
    data = json.loads(MANIFEST.read_text())
    return {entry["path"]: entry for entry in data["resources"]}


def input_evidence(paths: list[str] = STOCK_DIFFUSE_INPUTS) -> dict[str, dict[str, Any]]:
    by_path = load_manifest_entries()
    missing = [path for path in paths if path not in by_path]
    if missing:
        raise KeyError(f"resources missing from evidence manifest: {missing}")

    evidence: dict[str, dict[str, Any]] = {}
    for path in paths:
        entry = by_path[path]
        evidence[path] = {
            "evidence_label": entry["evidence_label"],
            "sha256": entry["sha256"],
            "size_bytes": entry["size_bytes"],
        }
    return evidence
