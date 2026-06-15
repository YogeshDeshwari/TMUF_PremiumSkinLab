from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from src.stock_diffuse.package import write_stable_zip_entry


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KIT_DIR = ROOT / "out" / "proof" / "tmuf_calibration_smoke_kit"
CALIBRATION_SKIN = ROOT / "out" / "skins" / "calibration_stock_diffuse.zip"
SMOKE_TEMPLATE = ROOT / "out" / "proof" / "calibration_tmuf_smoke_template.json"
CALIBRATION_ATLAS = ROOT / "out" / "previews" / "calibration_stock_diffuse_atlas.png"
CALIBRATION_PROJECTION = ROOT / "out" / "previews" / "calibration_stock_diffuse_projected_side_top_rear.png"
SMOKE_DOC = ROOT / "docs" / "tmuf_smoke_test.md"
KIT_FILES = {
    "skins/calibration_stock_diffuse.zip": CALIBRATION_SKIN,
    "proof/calibration_tmuf_smoke_template.json": SMOKE_TEMPLATE,
    "previews/calibration_stock_diffuse_atlas.png": CALIBRATION_ATLAS,
    "previews/calibration_stock_diffuse_projected_side_top_rear.png": CALIBRATION_PROJECTION,
    "README_tmuf_smoke_test.md": SMOKE_DOC,
}


def _copy_file(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def _kit_manifest(files: list[str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "not_run",
        "does_not_prove_tmuf_smoke": True,
        "calibration_skin": "skins/calibration_stock_diffuse.zip",
        "smoke_report_template": "proof/calibration_tmuf_smoke_template.json",
        "instructions": "README_tmuf_smoke_test.md",
        "files": files,
        "next_steps": [
            "Copy skins/calibration_stock_diffuse.zip into the TMUF/TMNF StadiumCar skin folder.",
            "Load the skin in TMUF/TMNF.",
            "Record required observations and screenshot paths in a filled smoke report.",
            "Run recipes/tmuf_smoke_gate.py --evaluate before applying any promotion.",
        ],
    }


def build_smoke_kit(out_dir: Path = DEFAULT_KIT_DIR) -> dict[str, str]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(KIT_FILES)
    for rel, src in KIT_FILES.items():
        _copy_file(src, out_dir / rel)

    manifest = _kit_manifest(files)
    manifest_path = out_dir / "kit_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    zip_path = out_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in files:
            write_stable_zip_entry(zf, rel, (out_dir / rel).read_bytes())
        write_stable_zip_entry(zf, "kit_manifest.json", manifest_path.read_bytes())

    return {
        "status": "not_run",
        "manifest": str(manifest_path),
        "zip": str(zip_path),
        "kit_dir": str(out_dir),
        "calibration_skin": str(out_dir / "skins" / "calibration_stock_diffuse.zip"),
    }


def install_calibration_skin(skins_dir: Path) -> dict[str, str | bool]:
    skins_dir = Path(skins_dir)
    skins_dir.mkdir(parents=True, exist_ok=True)
    dst = skins_dir / "calibration_stock_diffuse.zip"
    _copy_file(CALIBRATION_SKIN, dst)
    return {
        "status": "installed_not_tested",
        "installed_skin": str(dst),
        "does_not_prove_tmuf_smoke": True,
    }
