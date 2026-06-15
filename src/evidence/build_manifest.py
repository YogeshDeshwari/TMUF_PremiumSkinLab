from __future__ import annotations

import hashlib
import json
import struct
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
RESOURCES = ROOT / "resources"
MANIFEST = RESOURCES / "evidence_manifest.json"
EXCLUDED_RESOURCE_PARTS = {
    ("experimental", "flows", "remove_guards", "bin", "Debug"),
    ("experimental", "flows", "remove_guards", "obj"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def evidence_label(rel: Path) -> str:
    parts = rel.parts
    if parts[0] == "authoritative" and len(parts) > 1 and parts[1] == "gbuffer":
        return "experimental"
    if parts[0] == "authoritative":
        return "proven"
    if parts[0] == "reference_only":
        return "reference_only"
    if parts[0] == "experimental":
        return "experimental"
    return "experimental"


def usage_text(rel: Path, label: str) -> tuple[str, str]:
    name = rel.name
    if label == "proven":
        return (
            "Use as stock StadiumCar source evidence for Diffuse-only generation.",
            "Still requires TMUF smoke testing for final generated skins.",
        )
    if rel.parts[:2] == ("authoritative", "gbuffer"):
        return (
            "Use for 3D-position-driven calibration and candidate painting.",
            "Strong local provenance, but mapping remains experimental until calibration passes in TMUF.",
        )
    if name == "StadiumCarV2_primary_skin.zip":
        return (
            "Use as TMUF-era full package reference for file names, DDS slots, and visual inspiration.",
            "Reference-only because StadiumCar V2 uses new mapping and is not stock UV truth.",
        )
    if name == "Stafiumv2-DiffuseTemplate.zip":
        return (
            "Use as StadiumCar V2 wire/prelight reference.",
            "Reference-only because V2 mapping is not stock StadiumCar mapping.",
        )
    if name == "The_Diffuse_PSD_file.zip":
        return (
            "Use as community PSD cross-check.",
            "Reference-only because hash differs from the local CarPark PSD and provenance is community-uploaded.",
        )
    if name == "StadiumCar_HQ_Templates.zip":
        return (
            "Use high-resolution AO/prelight/wire overlays as visual reference.",
            "Reference-only because it is not the local stock PSD source of truth.",
        )
    if name == "Trackmania-Skin-Details-2021-02-18.zip":
        return (
            "Use only as modern Trackmania media reference.",
            "Rejected as TMUF/TMNF classic material-route authority.",
        )
    if name in {"CH_Blu.zip", "CH_Bloom_Wheel_LED_Underglow.zip"}:
        return (
            "Use as CH_2026 custom full-car reference for visual comparison of Diffuse, Details, ProjShad, dirty maps, and GBX packaging.",
            "Reference-only and not stock Diffuse-only truth; these packages stay outside the first stock calibration lane.",
        )
    if name.startswith("ugghost"):
        return (
            "Use as TMU/TMUF technical routing and custom-model workflow reference.",
            "Old guide; not proof that any generated package is TMUF-smoke-tested.",
        )
    if rel.parts[:2] == ("reference_only", "downloads") and name.endswith(".zip"):
        return (
            "Use as an external skin reference package for visual composition, texture-slot, and packaging analysis.",
            "Reference-only; package contents must be analyzed before borrowing any idea, and it is not stock mapping or TMUF smoke evidence.",
        )
    if name.endswith(".zip") and "CH_2026" in name:
        return (
            "Use only as explicit CH_2026 full-car donor profile for Details, ProjShad, and GBX experiments.",
            "Experimental donor/custom mesh path; not official stock country-skin packaging.",
        )
    if "canvas_compose" in rel.parts:
        return (
            "Use as historical implementation reference for CH_2026 full-car lane.",
            "Experimental until rewired to explicit profiles and tested in this lab.",
        )
    if "remove_guards" in rel.parts:
        return (
            "Use as historical GBX.NET guard-removal tool for CH_2026 no-mudguard experiments.",
            "Experimental until package output is smoke-tested in TMUF.",
        )
    return (
        "Use as reference material for the evidence-backed generator.",
        "No broader truth should be inferred without a proof gate.",
    )


def dds_metadata(data: bytes) -> dict[str, Any] | None:
    if len(data) < 128 or data[:4] != b"DDS ":
        return None
    return {
        "width": struct.unpack("<I", data[16:20])[0],
        "height": struct.unpack("<I", data[12:16])[0],
        "mip_count": struct.unpack("<I", data[28:32])[0],
        "fourcc": data[84:88].decode("ascii", errors="replace"),
    }


def metadata(path: Path) -> dict[str, Any]:
    suffix = path.suffix.lower()
    out: dict[str, Any] = {}
    if suffix in {".png", ".jpg", ".jpeg", ".tga"}:
        with Image.open(path) as img:
            out["image"] = {"width": img.width, "height": img.height, "mode": img.mode}
    elif suffix == ".dds":
        info = dds_metadata(path.read_bytes())
        if info:
            out["dds"] = info
    elif suffix == ".npy":
        arr = np.load(path, mmap_mode="r")
        out["npy"] = {"shape": list(arr.shape), "dtype": str(arr.dtype)}
    elif suffix == ".zip":
        try:
            with zipfile.ZipFile(path) as zf:
                out["zip"] = {"entries": zf.namelist()}
        except zipfile.BadZipFile:
            out["zip_error"] = "bad_zip"
    return out


def is_excluded_resource(rel: Path) -> bool:
    parts = rel.parts
    return any(parts[: len(prefix)] == prefix for prefix in EXCLUDED_RESOURCE_PARTS)


def build_manifest() -> dict[str, Any]:
    resources: list[dict[str, Any]] = []
    files = sorted(
        p
        for p in RESOURCES.rglob("*")
        if p.is_file()
        and p.name != MANIFEST.name
        and not is_excluded_resource(p.relative_to(RESOURCES))
    )
    for path in files:
        if path.stat().st_size == 0:
            continue
        rel = path.relative_to(RESOURCES)
        label = evidence_label(rel)
        safe_use, limits = usage_text(rel, label)
        resources.append(
            {
                "path": rel.as_posix(),
                "evidence_label": label,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "safe_use": safe_use,
                "limits": limits,
                "metadata": metadata(path),
            }
        )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "rules": {
            "proven": "Verified by local evidence or direct source file identity; still needs skin-output validation.",
            "reference_only": "Useful for comparison or visual study, not authoritative for stock TMUF StadiumCar.",
            "experimental": "Usable only behind proof gates; never a default truth.",
            "rejected": "Known wrong for this target.",
        },
        "resources": resources,
    }


def main() -> int:
    manifest = build_manifest()
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"wrote {MANIFEST} ({len(manifest['resources'])} resources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
