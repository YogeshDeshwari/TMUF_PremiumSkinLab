from __future__ import annotations

import json
import struct
import zipfile
from pathlib import Path
from typing import Any

from src.evidence.artifact_trace import sha256
from src.evidence.input_trace import MANIFEST, STOCK_DIFFUSE_INPUTS
from src.evidence.visual_quality import validate_visual_quality
from src.stock_diffuse.package import ZIP_TIMESTAMP
from src.stock_diffuse.premium import CANDIDATE_NAMES


ROOT = Path(__file__).resolve().parents[2]
REQUIRED_STOCK_SKINS = ["calibration_stock_diffuse", *CANDIDATE_NAMES]
STOCK_PACKAGE_FILES = {"Diffuse.dds", "Icon.dds"}
FORBIDDEN_STOCK_FILES = {"Details.dds", "ProjShad.dds"}
LOCAL_PSD_MASK_STATUS = "proven_local_psd_parts_label_map"
GBUFFER_PENDING_STATUS = "experimental_until_tmuf_smoke"
GBUFFER_PROVEN_STATUS = "proven_by_tmuf_smoke"
ALPHA_MIN_CONSERVATIVE = 100
ALPHA_MAX_CONSERVATIVE = 155


def dds_info(data: bytes) -> dict[str, Any]:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("not a DDS file")
    return {
        "width": struct.unpack("<I", data[16:20])[0],
        "height": struct.unpack("<I", data[12:16])[0],
        "mip_count": struct.unpack("<I", data[28:32])[0],
        "fourcc": data[84:88].decode("ascii", errors="replace"),
    }


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _manifest_by_path(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {entry["path"]: entry for entry in manifest["resources"]}


def validate_input_evidence(report: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    by_path = _manifest_by_path(manifest)
    input_evidence = report.get("input_evidence", {})

    for path in STOCK_DIFFUSE_INPUTS:
        if path not in input_evidence:
            errors.append(f"missing input evidence: {path}")
            continue
        if path not in by_path:
            errors.append(f"input evidence absent from manifest: {path}")
            continue

        actual = input_evidence[path]
        expected = by_path[path]
        if actual.get("evidence_label") != expected.get("evidence_label"):
            errors.append(f"input evidence label mismatch: {path}")
        elif actual.get("sha256") != expected.get("sha256"):
            errors.append(f"input evidence sha256 mismatch: {path}")
        elif actual.get("size_bytes") != expected.get("size_bytes"):
            errors.append(f"input evidence size mismatch: {path}")

    for path in input_evidence:
        if path not in by_path:
            errors.append(f"input evidence not in manifest: {path}")
        elif by_path[path].get("evidence_label") == "reference_only":
            errors.append(f"reference_only input used as stock truth: {path}")

    return errors


def validate_output_artifacts(report: dict[str, Any], root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    expected = {
        "skin_zip": f"out/skins/{report.get('skin_name')}.zip",
        "atlas_preview": f"out/previews/{report.get('skin_name')}_atlas.png",
        "projected_preview": f"out/previews/{report.get('skin_name')}_projected_side_top_rear.png",
    }
    output_artifacts = report.get("output_artifacts", {})
    for key, rel in expected.items():
        if key not in output_artifacts:
            errors.append(f"missing output artifact evidence: {key}")
            continue
        path = root / rel
        actual = output_artifacts[key]
        if actual.get("path") != rel:
            errors.append(f"output artifact path mismatch: {key}")
        elif not path.exists():
            errors.append(f"output artifact file missing: {rel}")
        elif actual.get("sha256") != sha256(path):
            errors.append(f"output artifact sha256 mismatch: {rel}")
        elif actual.get("size_bytes") != path.stat().st_size:
            errors.append(f"output artifact size mismatch: {rel}")
    return errors


def validate_mask_evidence(report: dict[str, Any], premium: bool) -> list[str]:
    if not premium:
        return []

    errors: list[str] = []
    masks_used = report.get("masks_used", [])
    mask_evidence = report.get("mask_evidence", {})
    if not isinstance(masks_used, list) or not masks_used:
        return ["premium report has no masks_used list"]
    if not isinstance(mask_evidence, dict):
        return ["premium report has no mask_evidence object"]
    gbuffer_proven = (
        report.get("tmuf_smoke_test") == "passed"
        and report.get("evidence_status", {}).get("gbuffer_mapping") == "proven_by_tmuf_smoke"
    )
    expected_gbuffer_status = GBUFFER_PROVEN_STATUS if gbuffer_proven else GBUFFER_PENDING_STATUS

    for name in masks_used:
        entry = mask_evidence.get(name)
        if not isinstance(entry, dict):
            errors.append(f"missing mask evidence: {name}")
            continue
        if entry.get("pixel_count", 0) <= 0:
            errors.append(f"mask evidence pixel count is empty: {name}")
        if not entry.get("source_files"):
            errors.append(f"mask evidence source files missing: {name}")

    mudguards = mask_evidence.get("mudguards", {})
    if mudguards.get("evidence_status") != LOCAL_PSD_MASK_STATUS:
        errors.append("mudguards must use proven local PSD label evidence")
    elif "resources/authoritative/parts/psd_parts_labels.npy" not in mudguards.get("source_files", []):
        errors.append("mudguards must cite psd_parts_labels.npy")

    for name in masks_used:
        if name == "mudguards":
            continue
        entry = mask_evidence.get(name, {})
        if entry.get("evidence_status") == LOCAL_PSD_MASK_STATUS:
            if "resources/authoritative/parts/psd_parts_labels.npy" not in entry.get("source_files", []):
                errors.append(f"{name} local PSD mask must cite psd_parts_labels.npy")
            continue
        if entry.get("evidence_status") != expected_gbuffer_status:
            if gbuffer_proven:
                errors.append(f"{name} must be proven by TMUF smoke after promotion")
            else:
                errors.append(f"{name} must stay experimental until TMUF smoke")

    return errors


def validate_alpha_policy(report: dict[str, Any], premium: bool) -> list[str]:
    if not premium:
        return []

    errors: list[str] = []
    policy = report.get("alpha_policy")
    metrics = report.get("alpha_metrics")
    if not isinstance(policy, dict):
        return ["premium report has no alpha_policy object"]
    if not isinstance(metrics, dict):
        return ["premium report has no alpha_metrics object"]

    if policy.get("route") != "conservative_dxt5_alpha":
        errors.append("alpha policy route must be conservative_dxt5_alpha")
    if policy.get("material_effect_status") != "not_proven_until_tmuf_smoke":
        errors.append("alpha material effect must remain unproven until TMUF smoke")
    if policy.get("tmuf_gloss_claim") != "none":
        errors.append("alpha policy must not claim TMUF gloss behavior")

    min_alpha = metrics.get("min_alpha")
    max_alpha = metrics.get("max_alpha")
    if not isinstance(min_alpha, int) or min_alpha < ALPHA_MIN_CONSERVATIVE:
        errors.append("alpha min below conservative range")
    if not isinstance(max_alpha, int) or max_alpha > ALPHA_MAX_CONSERVATIVE:
        errors.append("alpha max above conservative range")
    unique_values = metrics.get("unique_alpha_values", [])
    if not isinstance(unique_values, list) or not unique_values:
        errors.append("alpha metrics must include unique_alpha_values")
    high_ratio = metrics.get("high_alpha_pixel_ratio")
    if not isinstance(high_ratio, (int, float)) or high_ratio <= 0 or high_ratio >= 0.45:
        errors.append("alpha high-alpha pixel ratio outside conservative range")

    return errors


def validate_design_lane_evidence(report: dict[str, Any], premium: bool) -> list[str]:
    if not premium:
        return []

    errors: list[str] = []
    lane = report.get("design_lane")
    if not isinstance(lane, dict):
        return ["premium report has no design_lane object"]

    if not lane.get("lane_id"):
        errors.append("design lane must include lane_id")
    if not lane.get("composition_focus"):
        errors.append("design lane must include composition_focus")
    if lane.get("evidence_status") != "recipe_metadata_not_tmuf_proof":
        errors.append("design lane metadata must not claim TMUF proof")

    distinctive_masks = lane.get("distinctive_masks")
    if not isinstance(distinctive_masks, list) or len(distinctive_masks) < 2:
        errors.append("design lane must include at least two distinctive masks")
    else:
        masks_used = set(report.get("masks_used", []))
        if not set(distinctive_masks) <= masks_used:
            errors.append("design lane distinctive masks must be listed in masks_used")

    return errors


def validate_premium_lane_distinctness(skins: list[dict[str, Any]]) -> list[str]:
    lane_ids = [
        skin.get("design_lane", {}).get("lane_id")
        for skin in skins
        if skin.get("skin_name") != "calibration_stock_diffuse"
    ]
    lane_ids = [lane_id for lane_id in lane_ids if lane_id]
    if len(set(lane_ids)) != len(lane_ids):
        return ["premium design lanes must be distinct across candidates"]
    return []


def _known_panel_catalog_targets(root: Path = ROOT) -> set[str]:
    inventory_path = root / "out" / "reports" / "stock_part_inventory.json"
    if not inventory_path.exists():
        return set()
    inventory = _load_json(inventory_path)
    panels = inventory.get("paintable_panel_catalog", {}).get("panels", {})
    if not isinstance(panels, dict):
        return set()
    return set(panels)


def validate_panel_catalog_targets(
    report: dict[str, Any],
    premium: bool,
    root: Path = ROOT,
) -> list[str]:
    if not premium:
        return []

    targets = report.get("panel_catalog_targets")
    if not isinstance(targets, list) or not targets:
        return ["premium report has no panel_catalog_targets list"]

    errors: list[str] = []
    if len(set(targets)) != len(targets):
        errors.append("panel_catalog_targets must not contain duplicates")

    known_targets = _known_panel_catalog_targets(root)
    for target in targets:
        if target not in known_targets:
            errors.append(f"unknown panel catalog target: {target}")

    lane = report.get("design_lane", {})
    lane_targets = lane.get("primary_catalog_targets") if isinstance(lane, dict) else None
    if not isinstance(lane_targets, list) or sorted(lane_targets) != sorted(targets):
        errors.append("design lane primary_catalog_targets must match panel_catalog_targets")
    if not isinstance(lane, dict) or lane.get("catalog_target_count") != len(targets):
        errors.append("design lane catalog_target_count must match panel_catalog_targets")

    return errors


def validate_render_profile(report: dict[str, Any], premium: bool) -> list[str]:
    if not premium:
        return []

    profile = report.get("render_profile")
    if not isinstance(profile, dict):
        return ["premium report has no render_profile object"]

    errors: list[str] = []
    if profile.get("lane_specific_strengths") is not True:
        errors.append("render profile must declare lane_specific_strengths")
    if profile.get("evidence_status") != "recipe_metadata_not_tmuf_proof":
        errors.append("render profile metadata must not claim TMUF proof")

    masks_used = report.get("masks_used", [])
    mask_strengths = profile.get("mask_strengths")
    if not isinstance(mask_strengths, dict):
        errors.append("render profile has no mask_strengths object")
    else:
        for mask_name in masks_used:
            if mask_name not in mask_strengths:
                errors.append(f"missing render strength: {mask_name}")

    distinctive_masks = report.get("design_lane", {}).get("distinctive_masks", [])
    distinctive_strengths = profile.get("distinctive_mask_strengths")
    if not isinstance(distinctive_strengths, dict):
        errors.append("render profile has no distinctive_mask_strengths object")
    else:
        for mask_name in distinctive_masks:
            strength = distinctive_strengths.get(mask_name)
            if not isinstance(strength, (int, float)):
                errors.append(f"missing distinctive render strength: {mask_name}")
            elif strength < 1.0:
                errors.append(f"distinctive render strength must be >= 1.0: {mask_name}")

    mask_style_metrics = report.get("mask_style_metrics")
    if not isinstance(mask_style_metrics, dict):
        errors.append("premium report has no mask_style_metrics object")
    else:
        for mask_name in distinctive_masks:
            entry = mask_style_metrics.get(mask_name)
            if not isinstance(entry, dict):
                errors.append(f"missing mask style metrics: {mask_name}")
                continue
            if entry.get("pixel_count", 0) <= 0:
                errors.append(f"mask style metrics pixel count is empty: {mask_name}")
            if entry.get("mean_alpha", 0) <= 112:
                errors.append(f"distinctive mask mean alpha must exceed base alpha: {mask_name}")

    return errors


def validate_premium_batch_index(index: dict[str, Any], premium_reports: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if index.get("schema") != "tmuf_premium_skin_lab.premium_batch_index.v1":
        errors.append("premium batch index schema mismatch")
    if index.get("route") != "stock_diffuse_only":
        errors.append("premium batch index route must be stock_diffuse_only")
    if index.get("does_not_prove_tmuf_smoke") is not True:
        errors.append("premium batch index must not prove TMUF smoke")

    candidates = index.get("candidates")
    if not isinstance(candidates, list):
        return [*errors, "premium batch index candidates must be a list"]
    if index.get("candidate_count") != len(candidates):
        errors.append("premium batch index candidate_count mismatch")
    if len(candidates) != len(premium_reports):
        errors.append("premium batch index report count mismatch")

    report_by_name = {report.get("skin_name"): report for report in premium_reports}
    lane_ids: list[str] = []
    for candidate in candidates:
        name = candidate.get("skin_name")
        report = report_by_name.get(name)
        if not isinstance(report, dict):
            errors.append(f"premium batch index has unknown candidate: {name}")
            continue
        lane_id = candidate.get("design_lane", {}).get("lane_id")
        if lane_id:
            lane_ids.append(lane_id)
        if candidate.get("tmuf_smoke_test") != report.get("tmuf_smoke_test"):
            errors.append(f"premium batch index smoke status mismatch: {name}")
        if candidate.get("gbuffer_mapping") != report.get("evidence_status", {}).get("gbuffer_mapping"):
            errors.append(f"premium batch index gbuffer status mismatch: {name}")
        if candidate.get("package_files") != report.get("package_files"):
            errors.append(f"premium batch index package files mismatch: {name}")
        if candidate.get("design_lane", {}).get("lane_id") != report.get("design_lane", {}).get("lane_id"):
            errors.append(f"premium batch index design lane mismatch: {name}")
        if candidate.get("render_profile") != report.get("render_profile"):
            errors.append(f"premium batch index render profile mismatch: {name}")
        if candidate.get("panel_catalog_targets") != report.get("panel_catalog_targets"):
            errors.append(f"premium batch index panel catalog targets mismatch: {name}")
        if candidate.get("output_artifacts", {}).get("skin_zip", {}).get("path") != report.get("output_artifacts", {}).get("skin_zip", {}).get("path"):
            errors.append(f"premium batch index artifact mismatch: {name}")

    if len(set(lane_ids)) != len(lane_ids):
        errors.append("premium batch index lane IDs must be distinct")
    return errors


def _zip_checks(zip_path: Path) -> tuple[dict[str, bool], list[str]]:
    checks = {
        "zip_exists": zip_path.exists(),
        "zip_stock_diffuse_only": False,
        "zip_has_stable_timestamps": False,
        "dds_headers_valid": False,
    }
    errors: list[str] = []
    if not zip_path.exists():
        errors.append(f"missing zip: {zip_path}")
        return checks, errors

    try:
        with zipfile.ZipFile(zip_path) as zf:
            names = set(zf.namelist())
            checks["zip_stock_diffuse_only"] = names == STOCK_PACKAGE_FILES
            checks["zip_has_stable_timestamps"] = all(
                info.date_time == ZIP_TIMESTAMP for info in zf.infolist()
            )
            if not checks["zip_stock_diffuse_only"]:
                errors.append(f"stock zip has unexpected files: {zip_path}")
            if not checks["zip_has_stable_timestamps"]:
                errors.append(f"stock zip has non-deterministic timestamps: {zip_path}")

            if STOCK_PACKAGE_FILES.issubset(names):
                diffuse = dds_info(zf.read("Diffuse.dds"))
                icon = dds_info(zf.read("Icon.dds"))
                checks["dds_headers_valid"] = (
                    diffuse["width"] == 2048
                    and diffuse["height"] == 2048
                    and diffuse["fourcc"] == "DXT5"
                    and icon["width"] == 64
                    and icon["height"] == 64
                    and icon["fourcc"] == "DXT5"
                )
    except (zipfile.BadZipFile, ValueError) as exc:
        errors.append(f"invalid zip/dds: {zip_path}: {exc}")
        return checks, errors

    if not checks["dds_headers_valid"]:
        errors.append(f"DDS headers invalid: {zip_path}")
    return checks, errors


def _report_checks(report_path: Path, manifest: dict[str, Any]) -> tuple[dict[str, bool], dict[str, Any], list[str]]:
    checks = {
        "report_exists": report_path.exists(),
        "report_route_stock_diffuse_only": False,
        "report_declares_no_donor_or_details_route": False,
        "report_input_evidence_matches_manifest": False,
        "report_output_artifacts_match_files": False,
        "report_mask_evidence_valid": False,
        "report_alpha_policy_valid": False,
        "report_design_lane_valid": False,
        "report_panel_catalog_targets_valid": False,
        "report_render_profile_valid": False,
        "tmuf_smoke_passed": False,
    }
    errors: list[str] = []
    if not report_path.exists():
        errors.append(f"missing report: {report_path}")
        return checks, {}, errors

    report = _load_json(report_path)
    checks["report_route_stock_diffuse_only"] = report.get("route") == "stock_diffuse_only"
    package_files = set(report.get("package_files", []))
    forbidden = FORBIDDEN_STOCK_FILES & package_files
    checks["report_declares_no_donor_or_details_route"] = (
        package_files == STOCK_PACKAGE_FILES
        and not forbidden
        and report.get("evidence_status", {}).get("donor_gbx", "not_used") == "not_used"
    )
    input_errors = validate_input_evidence(report, manifest)
    output_errors = validate_output_artifacts(report)
    checks["report_input_evidence_matches_manifest"] = not input_errors
    checks["report_output_artifacts_match_files"] = not output_errors
    checks["tmuf_smoke_passed"] = (
        report.get("tmuf_smoke_test") == "passed"
        and report.get("evidence_status", {}).get("gbuffer_mapping") == "proven_by_tmuf_smoke"
    )

    if not checks["report_route_stock_diffuse_only"]:
        errors.append(f"report route is not stock_diffuse_only: {report_path}")
    if not checks["report_declares_no_donor_or_details_route"]:
        errors.append(f"report does not declare a clean stock route: {report_path}")
    errors.extend(f"{report_path}: {error}" for error in input_errors)
    errors.extend(f"{report_path}: {error}" for error in output_errors)
    return checks, report, errors


def _preview_checks(root: Path, skin_name: str) -> tuple[dict[str, bool], list[str]]:
    atlas = root / "out" / "previews" / f"{skin_name}_atlas.png"
    projection = root / "out" / "previews" / f"{skin_name}_projected_side_top_rear.png"
    checks = {
        "atlas_preview_exists": atlas.exists(),
        "projection_preview_exists": projection.exists(),
    }
    errors: list[str] = []
    if not atlas.exists():
        errors.append(f"missing atlas preview: {atlas}")
    if not projection.exists():
        errors.append(f"missing projection preview: {projection}")
    return checks, errors


def validate_stock_outputs(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    manifest = _load_json(root / MANIFEST.relative_to(ROOT))
    errors: list[str] = []
    skins: list[dict[str, Any]] = []
    premium_reports: list[dict[str, Any]] = []

    for skin_name in REQUIRED_STOCK_SKINS:
        premium = skin_name != "calibration_stock_diffuse"
        zip_checks, zip_errors = _zip_checks(root / "out" / "skins" / f"{skin_name}.zip")
        report_checks, report, report_errors = _report_checks(
            root / "out" / "reports" / f"{skin_name}.json",
            manifest,
        )
        mask_errors = validate_mask_evidence(report, premium=premium)
        alpha_errors = validate_alpha_policy(report, premium=premium)
        lane_errors = validate_design_lane_evidence(report, premium=premium)
        panel_catalog_errors = validate_panel_catalog_targets(report, premium=premium, root=root)
        render_profile_errors = validate_render_profile(report, premium=premium)
        if premium:
            premium_reports.append(report)
        report_checks["report_mask_evidence_valid"] = not mask_errors
        report_checks["report_alpha_policy_valid"] = not alpha_errors
        report_checks["report_design_lane_valid"] = not lane_errors
        report_checks["report_panel_catalog_targets_valid"] = not panel_catalog_errors
        report_checks["report_render_profile_valid"] = not render_profile_errors
        preview_checks, preview_errors = _preview_checks(root, skin_name)
        visual_checks, visual_metrics, visual_errors = validate_visual_quality(
            root,
            skin_name,
            premium=premium,
        )
        checks = {**zip_checks, **report_checks, **preview_checks, **visual_checks}
        skin_errors = [
            *zip_errors,
            *report_errors,
            *mask_errors,
            *alpha_errors,
            *lane_errors,
            *panel_catalog_errors,
            *render_profile_errors,
            *preview_errors,
            *visual_errors,
        ]
        errors.extend(skin_errors)
        skins.append(
            {
                "skin_name": skin_name,
                "checks": checks,
                "visual_metrics": visual_metrics,
                "errors": skin_errors,
                "tmuf_smoke_test": report.get("tmuf_smoke_test", "missing"),
                "gbuffer_mapping": report.get("evidence_status", {}).get("gbuffer_mapping", "missing"),
                "design_lane": report.get("design_lane", {}),
            }
        )

    errors.extend(validate_premium_lane_distinctness(skins))
    batch_index_path = root / "out" / "reports" / "premium_batch_index.json"
    batch_index: dict[str, Any] = {}
    batch_index_errors: list[str] = []
    if not batch_index_path.exists():
        batch_index_errors.append("missing premium batch index")
    else:
        batch_index = _load_json(batch_index_path)
        batch_index_errors.extend(validate_premium_batch_index(batch_index, premium_reports))
    errors.extend(batch_index_errors)
    all_smoke_passed = all(skin["checks"]["tmuf_smoke_passed"] for skin in skins)
    warnings = [] if all_smoke_passed else ["tmuf_smoke_pending"]
    local_checks_passed = not errors
    return {
        "local_checks_passed": local_checks_passed,
        "completion_status": "complete" if local_checks_passed and all_smoke_passed else "not_complete_tmuf_smoke_pending",
        "tmuf_smoke_status": "passed" if all_smoke_passed else "pending",
        "errors": errors,
        "warnings": warnings,
        "premium_batch_index": {
            "valid": not batch_index_errors,
            "candidate_count": batch_index.get("candidate_count", 0),
            "does_not_prove_tmuf_smoke": batch_index.get("does_not_prove_tmuf_smoke", True),
            "errors": batch_index_errors,
        },
        "skins": skins,
    }
