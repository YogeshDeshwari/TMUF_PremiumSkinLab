from __future__ import annotations

import hashlib
import json
import struct
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZipFile

from PIL import Image, ImageDraw, ImageOps, ImageStat


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT / "out" / "reference_analysis"
SCHEMA = "tmuf_premium_skin_lab.reference_package_analysis.v1"
CH_MESH_FILES = ("MainBody.Solid.Gbx", "MainBodyHigh.Solid.Gbx")
STOCK_FILES = {"diffuse.dds", "icon.dds"}
CUSTOM_FULLCAR_MARKERS = {
    "details.dds",
    "projshad.dds",
    "mainbody.solid.gbx",
    "mainbodyhigh.solid.gbx",
    "diffusedirty.dds",
    "detailsdirty.dds",
    "illum.dds",
}
CANONICAL_CASE = {
    "diffuse.dds": "Diffuse.dds",
    "details.dds": "Details.dds",
    "icon.dds": "Icon.dds",
    "projshad.dds": "ProjShad.dds",
    "diffusedirty.dds": "DiffuseDirty.dds",
    "detailsdirty.dds": "DetailsDirty.dds",
    "illum.dds": "Illum.dds",
    "mainbody.solid.gbx": "MainBody.Solid.Gbx",
    "mainbodyhigh.solid.gbx": "MainBodyHigh.Solid.Gbx",
}


def analyze_reference_package(
    package_zip: Path,
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    donor_zip: Path | None = None,
) -> dict[str, Any]:
    package_zip = Path(package_zip)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with ZipFile(package_zip) as zf:
        names = zf.namelist()
        entries = {name: _entry_info(zf, name) for name in names}
        dds = {name: _dds_info(zf.read(name)) for name in names if name.lower().endswith(".dds")}
        skin_json = _skin_json(zf)
        donor_mesh_match = _donor_mesh_match(zf, donor_zip)
        contact_sheet = _write_contact_sheet(zf, names, output_dir / f"{package_zip.stem}_contact_sheet.png")

    package_route, stock_lane_status = _classify_route(set(names), donor_mesh_match)
    report = {
        "schema": SCHEMA,
        "package_name": package_zip.name,
        "source_path": str(package_zip),
        "archive_sha256": _sha256_path(package_zip),
        "size_bytes": package_zip.stat().st_size,
        "package_route": package_route,
        "stock_lane_status": stock_lane_status,
        "evidence_label": "reference_only" if "reference" in package_route else "experimental",
        "does_not_prove_tmuf_smoke": True,
        "does_not_prove_stock_diffuse_mapping": True,
        "entries": entries,
        "dds": dds,
        "skin_json": skin_json,
        "filename_case_notes": _filename_case_notes(names),
        "donor_mesh_match": donor_mesh_match,
        "output_artifacts": {
            "report": str(output_dir / f"{package_zip.stem}_report.json"),
            "contact_sheet": str(contact_sheet),
        },
        "safe_use": _safe_use(package_route),
    }
    Path(report["output_artifacts"]["report"]).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def write_reference_package_index(
    reports: list[dict[str, Any]],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    gallery: Path | None = None,
    livery_gallery: Path | None = None,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "reference_package_index.json"
    path.write_text(
        json.dumps(
            {
                "schema": "tmuf_premium_skin_lab.reference_package_index.v1",
                "does_not_prove_tmuf_smoke": True,
                "gallery": str(gallery) if gallery is not None else None,
                "livery_atlas_gallery": str(livery_gallery) if livery_gallery is not None else None,
                "reports": [
                    {
                        "package_name": report["package_name"],
                        "package_route": report["package_route"],
                        "stock_lane_status": report["stock_lane_status"],
                        "archive_sha256": report["archive_sha256"],
                        "report": report["output_artifacts"]["report"],
                        "contact_sheet": report["output_artifacts"]["contact_sheet"],
                    }
                    for report in reports
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return path


def write_reference_package_gallery(reports: list[dict[str, Any]], output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    return _write_reference_gallery(
        reports,
        output_dir,
        output_name="reference_package_gallery.png",
        title_mode="package",
    )


def write_reference_livery_atlas_gallery(
    reports: list[dict[str, Any]], output_dir: Path = DEFAULT_OUTPUT_DIR
) -> Path:
    return _write_reference_gallery(
        reports,
        output_dir,
        output_name="reference_livery_atlas_gallery.png",
        title_mode="livery_atlas",
    )


def _write_reference_gallery(
    reports: list[dict[str, Any]],
    output_dir: Path,
    *,
    output_name: str,
    title_mode: str,
) -> Path:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cells: list[tuple[dict[str, Any], Image.Image]] = []
    for report in reports:
        if title_mode == "livery_atlas":
            preview = _livery_atlas_preview(Path(report["source_path"]))
        else:
            preview = _representative_preview(Path(report["source_path"]))
        cells.append((report, preview))

    columns = 4
    cell_w = 330
    cell_h = 285
    rows = max((len(cells) + columns - 1) // columns, 1)
    canvas = Image.new("RGB", (columns * cell_w, rows * cell_h), (7, 8, 10))
    draw = ImageDraw.Draw(canvas)
    for index, (report, preview) in enumerate(cells):
        col = index % columns
        row = index // columns
        x = col * cell_w
        y = row * cell_h
        route = report["package_route"]
        accent = _route_accent(route)
        draw.rectangle((x + 8, y + 8, x + cell_w - 8, y + cell_h - 8), outline=accent, width=2)
        draw.text((x + 18, y + 18), _shorten(report["package_name"], 34), fill=(235, 238, 242))
        draw.text((x + 18, y + 40), _shorten(route, 38), fill=accent)
        canvas.paste(preview, (x + 75, y + 68))
        dds_count = len(report.get("dds", {}))
        gbx_count = sum(1 for name in report.get("entries", {}) if name.lower().endswith(".gbx"))
        case_note = " case-variant" if report.get("filename_case_notes") else ""
        source = getattr(preview, "_tmuf_source_name", "preview")
        draw.text((x + 18, y + 230), f"slot: {_shorten(source, 28)}", fill=(180, 185, 194))
        draw.text((x + 18, y + 252), f"DDS {dds_count} / GBX {gbx_count}{case_note}", fill=(205, 207, 214))

    path = output_dir / output_name
    canvas.save(path)
    return path


def _classify_route(names: set[str], donor_mesh_match: dict[str, bool]) -> tuple[str, str]:
    lower_basenames = _lower_basenames(names)
    texture_names = {name for name in lower_basenames if name.endswith(".dds")}
    has_gbx = any(name.lower() in lower_basenames for name in CH_MESH_FILES)
    has_diffuse = "diffuse.dds" in lower_basenames
    has_details = "details.dds" in lower_basenames
    if texture_names == STOCK_FILES and not has_gbx:
        return "stock_diffuse_only_reference", "reference_only_not_generated_by_lab"
    if has_diffuse and has_details and has_gbx:
        if donor_mesh_match and all(donor_mesh_match.get(name) for name in CH_MESH_FILES):
            return "custom_fullcar_ch2026_reference", "not_stock_diffuse_only"
        if donor_mesh_match and any(donor_mesh_match.get(name) for name in CH_MESH_FILES):
            return "custom_fullcar_partial_ch2026_mesh_reference", "not_stock_diffuse_only"
        if donor_mesh_match:
            return "custom_fullcar_other_mesh_reference", "not_stock_diffuse_only"
        return "custom_fullcar_unverified_mesh_reference", "not_stock_diffuse_only"
    if has_gbx or (lower_basenames & CUSTOM_FULLCAR_MARKERS):
        return "custom_or_extended_reference_package", "not_stock_diffuse_only"
    return "unknown_reference_package", "not_stock_diffuse_only"


def _safe_use(package_route: str) -> str:
    if package_route == "custom_fullcar_ch2026_reference":
        return "Use only as CH_2026 custom full-car reference for Details/ProjShad/GBX lane analysis; never as stock StadiumCar truth."
    if package_route == "custom_fullcar_partial_ch2026_mesh_reference":
        return "Use only as custom full-car reference with partial CH_2026 donor overlap; never as universal mesh or stock StadiumCar truth."
    if package_route == "custom_fullcar_other_mesh_reference":
        return "Use only as custom full-car visual and packaging reference; mesh differs from the CH_2026 donor comparison."
    if package_route == "custom_fullcar_unverified_mesh_reference":
        return "Use only as custom full-car visual and packaging reference; no donor mesh comparison was provided."
    if package_route == "custom_or_extended_reference_package":
        return "Use only after manual inspection; package has custom or extended files and is not stock Diffuse-only proof."
    if package_route == "stock_diffuse_only_reference":
        return "Use as reference-only stock-format package; it still does not prove lab GBuffer mapping or TMUF load."
    return "Inspect manually before use; route is not recognized as stock proof."


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _entry_info(zf: ZipFile, name: str) -> dict[str, Any]:
    info = zf.getinfo(name)
    data = zf.read(name)
    return {
        "file_size": info.file_size,
        "compress_size": info.compress_size,
        "sha256": _sha256_bytes(data),
    }


def _dds_info(data: bytes) -> dict[str, Any]:
    if len(data) < 128 or data[:4] != b"DDS ":
        return {"valid": False}
    fourcc = data[84:88].decode("ascii", errors="replace").rstrip("\x00")
    return {
        "valid": True,
        "height": struct.unpack("<I", data[12:16])[0],
        "width": struct.unpack("<I", data[16:20])[0],
        "linear_size": struct.unpack("<I", data[20:24])[0],
        "mip_count": struct.unpack("<I", data[28:32])[0],
        "fourcc": fourcc or "RGBA8",
    }


def _skin_json(zf: ZipFile) -> dict[str, Any]:
    if "skin.json" not in zf.namelist():
        return {}
    try:
        data = json.loads(zf.read("skin.json").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"parse_error": True}
    return data if isinstance(data, dict) else {"value": data}


def _donor_mesh_match(zf: ZipFile, donor_zip: Path | None) -> dict[str, bool]:
    if donor_zip is None:
        return {}
    with ZipFile(donor_zip) as donor:
        result: dict[str, bool] = {}
        for name in CH_MESH_FILES:
            if name not in zf.namelist() or name not in donor.namelist():
                result[name] = False
                continue
            result[name] = _sha256_bytes(zf.read(name)) == _sha256_bytes(donor.read(name))
        return result


def _lower_basenames(names: set[str]) -> set[str]:
    return {Path(name).name.lower() for name in names if Path(name).name}


def _filename_case_notes(names: list[str]) -> list[dict[str, str]]:
    notes = []
    for name in names:
        base = Path(name).name
        canonical = CANONICAL_CASE.get(base.lower())
        if canonical is not None and base != canonical:
            notes.append({"entry": name, "expected_canonical_case": canonical})
    return notes


def _representative_preview(package_zip: Path) -> Image.Image:
    with ZipFile(package_zip) as zf:
        names = zf.namelist()
        dds_names = [name for name in names if name.lower().endswith(".dds")]
        if not dds_names:
            return Image.new("RGB", (180, 180), (42, 18, 18))
        preferred = max(dds_names, key=lambda name: _visual_score(name, zf.read(name)))
        try:
            image = Image.open(BytesIO(zf.read(preferred))).convert("RGBA")
            rgb = _enhanced_scan_preview(image)
            rgb.thumbnail((180, 180), Image.Resampling.LANCZOS)
            image.thumbnail((180, 180), Image.Resampling.LANCZOS)
            preview = Image.new("RGB", (180, 180), (13, 14, 17))
            preview.paste(rgb, ((180 - rgb.width) // 2, (180 - rgb.height) // 2))
            preview._tmuf_source_name = Path(preferred).name  # type: ignore[attr-defined]
            return preview
        except Exception:
            return Image.new("RGB", (180, 180), (42, 18, 18))


def _livery_atlas_preview(package_zip: Path) -> Image.Image:
    with ZipFile(package_zip) as zf:
        names = zf.namelist()
        dds_names = [name for name in names if name.lower().endswith(".dds")]
        livery_names = [
            name
            for name in dds_names
            if Path(name).name.lower() in {"diffuse.dds", "details.dds", "diffusedirty.dds", "detailsdirty.dds"}
        ]
        candidates = livery_names or dds_names
        if not candidates:
            return Image.new("RGB", (180, 180), (42, 18, 18))
        preferred = max(candidates, key=lambda name: _livery_visual_score(name, zf.read(name)))
        try:
            image = Image.open(BytesIO(zf.read(preferred))).convert("RGBA")
            rgb = _enhanced_scan_preview(image)
            rgb.thumbnail((180, 180), Image.Resampling.LANCZOS)
            preview = Image.new("RGB", (180, 180), (13, 14, 17))
            preview.paste(rgb, ((180 - rgb.width) // 2, (180 - rgb.height) // 2))
            preview._tmuf_source_name = Path(preferred).name  # type: ignore[attr-defined]
            return preview
        except Exception:
            return Image.new("RGB", (180, 180), (42, 18, 18))


def _visual_score(name: str, data: bytes) -> float:
    try:
        image = Image.open(BytesIO(data)).convert("RGBA")
    except Exception:
        return -1.0
    rgb = image.convert("RGB")
    rgb.thumbnail((128, 128), Image.Resampling.LANCZOS)
    stat = ImageStat.Stat(rgb)
    mean = stat.mean
    stdev = stat.stddev
    channel_spread = max(mean) - min(mean)
    score = sum(stdev) + channel_spread + (sum(mean) / 30.0)
    lower = Path(name).name.lower()
    if lower == "details.dds":
        score += 45.0
    elif lower == "diffuse.dds":
        score += 40.0
    elif lower == "icon.dds":
        score += 20.0
    elif lower in {"diffusedirty.dds", "detailsdirty.dds"}:
        score -= 35.0
    elif lower == "projshad.dds":
        score -= 40.0
    elif lower == "illum.dds":
        score -= 20.0
    return score


def _livery_visual_score(name: str, data: bytes) -> float:
    score = _visual_score(name, data)
    lower = Path(name).name.lower()
    if lower == "details.dds":
        score += 90.0
    elif lower == "diffuse.dds":
        score += 80.0
    elif lower in {"detailsdirty.dds", "diffusedirty.dds"}:
        score -= 60.0
    elif lower == "icon.dds":
        score -= 200.0
    elif lower == "projshad.dds":
        score -= 180.0
    return score


def _enhanced_scan_preview(image: Image.Image) -> Image.Image:
    rgb = image.convert("RGB")
    stat = ImageStat.Stat(rgb)
    mean = sum(stat.mean) / 3.0
    contrast = sum(stat.stddev) / 3.0
    if mean < 90 or contrast < 35:
        rgb = ImageOps.autocontrast(rgb, cutoff=1)
        enhancer = ImageOps.autocontrast(rgb)
        rgb = Image.blend(rgb, enhancer, 0.35)
    return rgb


def _route_accent(route: str) -> tuple[int, int, int]:
    if route == "stock_diffuse_only_reference":
        return (92, 220, 150)
    if route == "custom_fullcar_ch2026_reference":
        return (80, 190, 255)
    if "partial" in route:
        return (255, 190, 85)
    if "other_mesh" in route:
        return (255, 125, 150)
    return (180, 170, 210)


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 1)] + "..."


def _write_contact_sheet(zf: ZipFile, names: list[str], path: Path) -> Path:
    dds_names = [name for name in names if name.lower().endswith(".dds")]
    cells: list[tuple[str, Image.Image]] = []
    for name in dds_names:
        try:
            image = Image.open(BytesIO(zf.read(name))).convert("RGBA")
            image.thumbnail((220, 220), Image.Resampling.LANCZOS)
            preview = Image.new("RGB", (220, 220), (12, 12, 14))
            preview.paste(image.convert("RGB"), ((220 - image.width) // 2, (220 - image.height) // 2))
        except Exception:
            preview = Image.new("RGB", (220, 220), (40, 10, 10))
        cells.append((name, preview))

    columns = 3
    rows = max((len(cells) + columns - 1) // columns, 1)
    canvas = Image.new("RGB", (columns * 260, rows * 260), (8, 8, 10))
    draw = ImageDraw.Draw(canvas)
    for index, (name, preview) in enumerate(cells):
        col = index % columns
        row = index // columns
        x = col * 260 + 20
        y = row * 260 + 28
        draw.text((x, y - 20), name, fill=(230, 230, 235))
        canvas.paste(preview, (x, y))
    canvas.save(path)
    return path
