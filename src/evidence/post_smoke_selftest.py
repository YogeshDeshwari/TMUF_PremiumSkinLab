from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from src.evidence.smoke_gate import apply_smoke_result
from src.evidence.smoke_record import record_calibration_smoke_report
from src.evidence.stock_validator import validate_stock_outputs
from src.profiles.gates import evaluate_profile_gates


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_COPY_PATHS = [
    "resources/evidence_manifest.json",
    "out/reports",
    "out/skins",
    "out/previews",
]
SCREENSHOT_ROLES = ("front", "side", "rear", "top")
WORKSPACE_MARKER = ".tmuf_premium_synthetic_workspace"


def _copy_required_paths(source_root: Path, workspace_root: Path) -> None:
    for rel in REQUIRED_COPY_PATHS:
        source = source_root / rel
        destination = workspace_root / rel
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def _write_synthetic_screenshots(workspace_root: Path) -> dict[str, Path]:
    screenshot_dir = workspace_root / "out" / "proof" / "synthetic_tmuf_smoke_inputs"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    screenshots: dict[str, Path] = {}
    colors = {
        "front": (220, 20, 180),
        "side": (0, 210, 240),
        "rear": (40, 70, 230),
        "top": (245, 245, 245),
    }
    for index, role in enumerate(SCREENSHOT_ROLES):
        path = screenshot_dir / f"synthetic_{role}.png"
        image = Image.new("RGB", (96, 64), (8, 10, 12))
        draw = ImageDraw.Draw(image)
        draw.rectangle((8, 8, 88, 56), fill=colors[role])
        draw.line((8, 16 + index * 6, 88, 48 - index * 4), fill=(15, 15, 15), width=3)
        image.save(path)
        screenshots[role] = path
    return screenshots


def run_synthetic_post_smoke_selftest(
    *,
    source_root: Path = ROOT,
    workspace_root: Path,
) -> dict[str, Any]:
    source_root = Path(source_root)
    workspace_root = Path(workspace_root)
    if source_root.resolve() == workspace_root.resolve():
        raise ValueError("synthetic self-test workspace must not be the source root")

    if workspace_root.exists():
        marker = workspace_root / WORKSPACE_MARKER
        if not marker.exists():
            raise ValueError(f"refusing to remove unmarked synthetic workspace: {workspace_root}")
        shutil.rmtree(workspace_root)
    workspace_root.mkdir(parents=True)
    (workspace_root / WORKSPACE_MARKER).write_text(
        "TMUF PremiumSkinLab synthetic post-smoke workspace; safe to recreate.\n"
    )
    _copy_required_paths(source_root, workspace_root)

    smoke_report = workspace_root / "out" / "proof" / "synthetic_calibration_tmuf_smoke.json"
    record_calibration_smoke_report(
        output_path=smoke_report,
        tester="synthetic self-test",
        tmuf_build="synthetic validator workspace, not TMUF",
        test_date_local="2026-06-15",
        screenshot_roles=_write_synthetic_screenshots(workspace_root),
        all_required_observations_passed=True,
        notes="Synthetic post-smoke pipeline self-test. This is not real TMUF/TMNF evidence.",
        base_dir=workspace_root,
    )
    report_paths = sorted((workspace_root / "out" / "reports").glob("*.json"))
    updated = apply_smoke_result(smoke_report, report_paths=report_paths, base_dir=workspace_root)
    stock = validate_stock_outputs(workspace_root)
    profiles = evaluate_profile_gates(workspace_root)

    return {
        "schema": "tmuf_premium_skin_lab.synthetic_post_smoke_selftest.v1",
        "synthetic_smoke": True,
        "writes_source_root": False,
        "claims_real_tmuf_proof": False,
        "source_root": source_root.as_posix(),
        "workspace_root": workspace_root.as_posix(),
        "smoke_report": smoke_report.relative_to(workspace_root).as_posix(),
        "updated_reports": [path.relative_to(workspace_root).as_posix() for path in updated],
        "stock": stock,
        "profiles": profiles,
        "limits": [
            "synthetic_only_not_real_tmuf_evidence",
            "does_not_replace_manual_calibration_smoke_test",
            "safe_for_pipeline_validation_only",
        ],
    }


def write_synthetic_post_smoke_selftest_report(
    *,
    output_path: Path,
    source_root: Path = ROOT,
    workspace_root: Path,
) -> Path:
    result = run_synthetic_post_smoke_selftest(
        source_root=source_root,
        workspace_root=workspace_root,
    )
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return output_path
