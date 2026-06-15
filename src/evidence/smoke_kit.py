from __future__ import annotations

import json
import shutil
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from src.evidence.skin_dirs import build_skin_dir_report, route_for_stadiumcar_skin_dir
from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS, REQUIRED_SCREENSHOT_ROLES
from src.stock_diffuse.package import write_stable_zip_entry
from src.stock_diffuse.panel_probe import PANEL_PROBE_NAME, save_outputs as save_panel_probe_outputs
from src.stock_diffuse.premium import CANDIDATE_NAMES


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KIT_DIR = ROOT / "out" / "proof" / "tmuf_calibration_smoke_kit"
CALIBRATION_SKIN = ROOT / "out" / "skins" / "calibration_stock_diffuse.zip"
SMOKE_TEMPLATE = ROOT / "out" / "proof" / "calibration_tmuf_smoke_template.json"
CALIBRATION_ATLAS = ROOT / "out" / "previews" / "calibration_stock_diffuse_atlas.png"
CALIBRATION_PROJECTION = ROOT / "out" / "previews" / "calibration_stock_diffuse_projected_side_top_rear.png"
PANEL_PROBE_SKIN = ROOT / "out" / "skins" / f"{PANEL_PROBE_NAME}.zip"
PANEL_PROBE_REPORT = ROOT / "out" / "reports" / f"{PANEL_PROBE_NAME}.json"
PANEL_PROBE_ATLAS = ROOT / "out" / "previews" / f"{PANEL_PROBE_NAME}_atlas.png"
PANEL_PROBE_PROJECTION = ROOT / "out" / "previews" / f"{PANEL_PROBE_NAME}_projected_side_top_rear.png"
SMOKE_CONTACT_SHEET = ROOT / "out" / "proof" / "tmuf_smoke_contact_sheet.png"
SMOKE_RUN_MANIFEST = ROOT / "out" / "proof" / "tmuf_smoke_run_manifest.json"
SMOKE_DOC = ROOT / "docs" / "tmuf_smoke_test.md"
KIT_FILES = {
    "skins/calibration_stock_diffuse.zip": CALIBRATION_SKIN,
    f"skins/{PANEL_PROBE_NAME}.zip": PANEL_PROBE_SKIN,
    f"reports/{PANEL_PROBE_NAME}.json": PANEL_PROBE_REPORT,
    "proof/calibration_tmuf_smoke_template.json": SMOKE_TEMPLATE,
    "proof/tmuf_smoke_run_manifest.json": SMOKE_RUN_MANIFEST,
    "previews/calibration_stock_diffuse_atlas.png": CALIBRATION_ATLAS,
    "previews/calibration_stock_diffuse_projected_side_top_rear.png": CALIBRATION_PROJECTION,
    f"previews/{PANEL_PROBE_NAME}_atlas.png": PANEL_PROBE_ATLAS,
    f"previews/{PANEL_PROBE_NAME}_projected_side_top_rear.png": PANEL_PROBE_PROJECTION,
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
        "supplemental_panel_probe_skin": f"skins/{PANEL_PROBE_NAME}.zip",
        "smoke_report_template": "proof/calibration_tmuf_smoke_template.json",
        "smoke_run_manifest": "proof/tmuf_smoke_run_manifest.json",
        "instructions": "README_tmuf_smoke_test.md",
        "files": files,
        "next_steps": [
            "Copy skins/calibration_stock_diffuse.zip into the TMUF/TMNF StadiumCar skin folder.",
            "Load the skin in TMUF/TMNF.",
            f"Optionally load skins/{PANEL_PROBE_NAME}.zip after the main calibration skin to inspect panel-family visibility.",
            "Record required observations, screenshots, and the install receipt with recipes/record_tmuf_smoke.py.",
            "Run recipes/tmuf_smoke_gate.py --evaluate before applying any promotion.",
        ],
    }


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _record_command_template() -> list[str]:
    command = [
        "python3",
        "recipes/record_tmuf_smoke.py",
        "--tester",
        "\"manual tester\"",
        "--tmuf-build",
        "\"TMUF local install\"",
        "--test-date-local",
        "YYYY-MM-DD",
        "--install-receipt",
        "out/proof/tmuf_calibration_smoke_kit/proof/calibration_install_receipt.json",
    ]
    for role in REQUIRED_SCREENSHOT_ROLES:
        command.extend(["--screenshot-role", f"{role}=/absolute/path/to/tmuf_{role}.png"])
    for observation in REQUIRED_OBSERVATIONS:
        command.extend(["--confirm-observation", observation])
    return command


def build_smoke_run_manifest(
    path: Path = SMOKE_RUN_MANIFEST,
    *,
    discovery_roots: list[Path] | None = None,
) -> Path:
    path = Path(path)
    data = {
        "schema": "tmuf_premium_skin_lab.tmuf_smoke_run_manifest.v1",
        "status": "not_run",
        "does_not_prove_tmuf_smoke": True,
        "route": "stock_diffuse_only",
        "artifact": "out/skins/calibration_stock_diffuse.zip",
        "kit_calibration_skin": "skins/calibration_stock_diffuse.zip",
        "supplemental_artifacts": {
            "panel_family_probe": {
                "kit_skin": f"skins/{PANEL_PROBE_NAME}.zip",
                "kit_report": f"reports/{PANEL_PROBE_NAME}.json",
                "kit_projection_preview": f"previews/{PANEL_PROBE_NAME}_projected_side_top_rear.png",
                "does_not_prove_tmuf_smoke": True,
                "purpose": "Inspect panel-family runtime visibility after the main calibration route loads.",
            },
        },
        "kit_smoke_report_template": "proof/calibration_tmuf_smoke_template.json",
        "required_screenshot_roles": REQUIRED_SCREENSHOT_ROLES,
        "required_observations": REQUIRED_OBSERVATIONS,
        "install_discovery": build_skin_dir_report(discovery_roots),
        "commands": {
            "record_explicit_observations": _record_command_template(),
            "evaluate": [
                "python3",
                "recipes/tmuf_smoke_gate.py",
                "--evaluate",
                "out/proof/calibration_tmuf_smoke.json",
            ],
            "apply_after_pass_only": [
                "python3",
                "recipes/tmuf_smoke_gate.py",
                "--apply",
                "out/proof/calibration_tmuf_smoke.json",
            ],
        },
        "promotion_rule": "Do not apply the smoke gate unless evaluation returns passed.",
        "known_limits": [
            "This manifest does not prove TMUF smoke status.",
            "Projected previews and contact sheets are review aids only.",
            "GBuffer mapping remains experimental until this run is completed and evaluated.",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return path


def build_smoke_contact_sheet(path: Path = SMOKE_CONTACT_SHEET) -> Path:
    items = [
        ("calibration_stock_diffuse", CALIBRATION_PROJECTION),
        (PANEL_PROBE_NAME, PANEL_PROBE_PROJECTION),
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


def build_smoke_kit(
    out_dir: Path = DEFAULT_KIT_DIR,
    *,
    discovery_roots: list[Path] | None = None,
) -> dict[str, str]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    save_panel_probe_outputs()
    build_smoke_contact_sheet()
    build_smoke_run_manifest(discovery_roots=discovery_roots)

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


def _install_entry(name: str, source: Path, destination: Path, *, purpose: str) -> dict[str, str | int | bool]:
    return {
        "name": name,
        "installed_skin": str(destination),
        "source_skin": str(source),
        "sha256": _digest(destination),
        "source_sha256": _digest(source),
        "size_bytes": destination.stat().st_size,
        "purpose": purpose,
        "does_not_prove_tmuf_smoke": True,
    }


def install_calibration_skin(
    skins_dir: Path,
    *,
    include_panel_probe: bool = False,
) -> dict[str, Any]:
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

    supplemental: list[dict[str, str | int | bool]] = []
    if include_panel_probe:
        save_panel_probe_outputs()
        probe_dst = skins_dir / f"{PANEL_PROBE_NAME}.zip"
        _copy_file(PANEL_PROBE_SKIN, probe_dst)
        supplemental.append(
            _install_entry(
                PANEL_PROBE_NAME,
                PANEL_PROBE_SKIN,
                probe_dst,
                purpose="panel_family_runtime_visibility_probe",
            )
        )

    return {
        "status": "installed_not_tested",
        "selection_mode": "explicit_install_target",
        "installed_skin": str(dst),
        "source_skin": str(CALIBRATION_SKIN),
        "route": route,
        "sha256": _digest(dst),
        "source_sha256": _digest(CALIBRATION_SKIN),
        "size_bytes": dst.stat().st_size,
        "installed_supplemental_skins": supplemental,
        "does_not_prove_tmuf_smoke": True,
    }


def install_discovered_calibration_skin(
    roots: list[Path] | None = None,
    *,
    include_panel_probe: bool = False,
) -> dict[str, Any]:
    discovery = build_skin_dir_report(roots)
    candidates = discovery["candidates"]
    if len(candidates) != 1:
        raise ValueError(
            "Discovered install requires exactly one recognized StadiumCar skin directory; "
            f"found {len(candidates)}"
        )
    selected = candidates[0]
    result = install_calibration_skin(
        Path(selected["path"]),
        include_panel_probe=include_panel_probe,
    )
    result["selection_mode"] = "single_discovered_candidate"
    result["selected_candidate"] = selected
    result["discovery"] = discovery
    return result


def write_install_receipt(install_result: dict[str, Any], out_dir: Path = DEFAULT_KIT_DIR) -> Path:
    out_dir = Path(out_dir)
    receipt_path = out_dir / "proof" / "calibration_install_receipt.json"
    data = {
        "schema": "tmuf_premium_skin_lab.calibration_install_receipt.v1",
        "status": install_result["status"],
        "selection_mode": install_result.get("selection_mode", "explicit_install_target"),
        "route": install_result["route"],
        "installed_skin": install_result["installed_skin"],
        "source_skin": install_result["source_skin"],
        "sha256": install_result["sha256"],
        "source_sha256": install_result["source_sha256"],
        "size_bytes": install_result["size_bytes"],
        "installed_supplemental_skins": install_result.get("installed_supplemental_skins", []),
        "does_not_prove_tmuf_smoke": True,
        "next_required_evidence": [
            "run_tmuf_calibration_smoke_test",
            "capture_front_side_rear_top_screenshots",
            "inspect_panel_family_probe_in_tmuf",
            "record_tmuf_smoke_evidence",
            "evaluate_then_apply_tmuf_smoke_gate",
        ],
    }
    if "selected_candidate" in install_result:
        data["selected_candidate"] = install_result["selected_candidate"]
    if "discovery" in install_result:
        data["discovery"] = install_result["discovery"]
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return receipt_path
