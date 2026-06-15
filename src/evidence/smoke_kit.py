from __future__ import annotations

import json
import shutil
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from src.evidence.skin_dirs import route_for_stadiumcar_skin_dir
from src.stock_diffuse.package import write_stable_zip_entry
from src.stock_diffuse.premium import CANDIDATE_NAMES


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KIT_DIR = ROOT / "out" / "proof" / "tmuf_calibration_smoke_kit"
CALIBRATION_SKIN = ROOT / "out" / "skins" / "calibration_stock_diffuse.zip"
SMOKE_TEMPLATE = ROOT / "out" / "proof" / "calibration_tmuf_smoke_template.json"
CALIBRATION_ATLAS = ROOT / "out" / "previews" / "calibration_stock_diffuse_atlas.png"
CALIBRATION_PROJECTION = ROOT / "out" / "previews" / "calibration_stock_diffuse_projected_side_top_rear.png"
SMOKE_CONTACT_SHEET = ROOT / "out" / "proof" / "tmuf_smoke_contact_sheet.png"
SMOKE_DOC = ROOT / "docs" / "tmuf_smoke_test.md"
KIT_FILES = {
    "skins/calibration_stock_diffuse.zip": CALIBRATION_SKIN,
    "proof/calibration_tmuf_smoke_template.json": SMOKE_TEMPLATE,
    "previews/calibration_stock_diffuse_atlas.png": CALIBRATION_ATLAS,
    "previews/calibration_stock_diffuse_projected_side_top_rear.png": CALIBRATION_PROJECTION,
    "previews/tmuf_smoke_contact_sheet.png": SMOKE_CONTACT_SHEET,
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
            "Record required observations and screenshot paths with recipes/record_tmuf_smoke.py.",
            "Run recipes/tmuf_smoke_gate.py --evaluate before applying any promotion.",
        ],
    }


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build_smoke_contact_sheet(path: Path = SMOKE_CONTACT_SHEET) -> Path:
    items = [
        ("calibration_stock_diffuse", CALIBRATION_PROJECTION),
        *[
            (name, ROOT / "out" / "previews" / f"{name}_projected_side_top_rear.png")
            for name in CANDIDATE_NAMES
        ],
    ]
    thumb_w, thumb_h = 420, 246
    label_h = 34
    margin = 20
    gap = 14
    columns = 3
    rows = (len(items) + columns - 1) // columns
    width = margin * 2 + columns * thumb_w + (columns - 1) * gap
    height = margin * 2 + rows * (thumb_h + label_h) + (rows - 1) * gap

    sheet = Image.new("RGB", (width, height), (10, 10, 12))
    draw = ImageDraw.Draw(sheet)
    for index, (name, source) in enumerate(items):
        if not source.exists():
            raise FileNotFoundError(source)
        row, column = divmod(index, columns)
        x = margin + column * (thumb_w + gap)
        y = margin + row * (thumb_h + label_h + gap)

        image = Image.open(source).convert("RGB")
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (thumb_w, thumb_h), (18, 18, 22))
        canvas.paste(image, ((thumb_w - image.width) // 2, (thumb_h - image.height) // 2))
        sheet.paste(canvas, (x, y + label_h))
        draw.text((x, y), name, fill=(235, 235, 240))
        draw.rectangle((x, y + label_h, x + thumb_w - 1, y + label_h + thumb_h - 1), outline=(70, 70, 78))

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


def validate_smoke_kit(out_dir: Path = DEFAULT_KIT_DIR) -> dict[str, Any]:
    out_dir = Path(out_dir)
    manifest_path = out_dir / "kit_manifest.json"
    zip_path = out_dir.with_suffix(".zip")

    missing_files = [rel for rel in sorted(KIT_FILES) if not (out_dir / rel).exists()]
    stale_files = [
        rel
        for rel, source in KIT_FILES.items()
        if (out_dir / rel).exists() and source.exists() and _digest(out_dir / rel) != _digest(source)
    ]

    zip_missing_or_stale: list[str] = []
    if not zip_path.exists():
        zip_missing_or_stale = sorted(KIT_FILES) + ["kit_manifest.json"]
    else:
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            expected_names = set(KIT_FILES) | {"kit_manifest.json"}
            zip_missing_or_stale.extend(sorted(expected_names - names))
            for rel, source in KIT_FILES.items():
                if rel in names and source.exists() and sha256(zf.read(rel)).hexdigest() != _digest(source):
                    zip_missing_or_stale.append(rel)
            if "kit_manifest.json" in names and manifest_path.exists():
                if sha256(zf.read("kit_manifest.json")).hexdigest() != _digest(manifest_path):
                    zip_missing_or_stale.append("kit_manifest.json")

    exists = manifest_path.exists() and zip_path.exists() and not missing_files
    fresh = exists and not stale_files and not zip_missing_or_stale
    status = "fresh_not_run" if fresh else "stale_or_missing"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        manifest_status = manifest.get("status", "unknown")
    else:
        manifest_status = "missing"

    return {
        "exists": exists,
        "fresh": fresh,
        "status": status,
        "manifest_status": manifest_status,
        "manifest": str(manifest_path),
        "zip": str(zip_path),
        "missing_files": missing_files,
        "stale_files": sorted(stale_files),
        "zip_missing_or_stale": sorted(set(zip_missing_or_stale)),
        "does_not_prove_tmuf_smoke": True,
    }


def build_smoke_kit(out_dir: Path = DEFAULT_KIT_DIR) -> dict[str, str]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    build_smoke_contact_sheet()

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
    if not skins_dir.exists():
        raise FileNotFoundError(skins_dir)
    if not skins_dir.is_dir():
        raise NotADirectoryError(skins_dir)
    route = route_for_stadiumcar_skin_dir(skins_dir)
    if route is None:
        raise ValueError(f"Install target is not a recognized StadiumCar skin directory: {skins_dir}")

    dst = skins_dir / "calibration_stock_diffuse.zip"
    _copy_file(CALIBRATION_SKIN, dst)
    return {
        "status": "installed_not_tested",
        "installed_skin": str(dst),
        "source_skin": str(CALIBRATION_SKIN),
        "route": route,
        "sha256": _digest(dst),
        "source_sha256": _digest(CALIBRATION_SKIN),
        "size_bytes": dst.stat().st_size,
        "does_not_prove_tmuf_smoke": True,
    }
