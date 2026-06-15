from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

from src.dds.tmnf_dds import build_dds_dxt5_bytes
from src.evidence.artifact_trace import stock_output_artifacts
from src.evidence.input_trace import PREMIUM_DIFFUSE_INPUTS, input_evidence
from src.evidence.panel_deep_dive import (
    GENERATOR_MASKS_NOT_CATALOG_PANELS,
    SURFACE_FAMILIES,
    _format_counts,
    _status_counts,
)
from src.evidence.part_inventory import build_part_inventory
from src.stock_diffuse.calibration import REF_DIR, SIZE, hx, load_fields, project_view
from src.stock_diffuse.package import write_stable_zip_entry
from src.stock_diffuse.panel_masks import build_stock_panel_masks


ROOT = Path(__file__).resolve().parents[2]
PANEL_PROBE_NAME = "calibration_panel_family_probe"
FAMILY_COLORS = {
    "front_nose_centerline": "#ff3030",
    "cockpit_mid_deck": "#00d8ff",
    "side_flanks_aero": "#20d060",
    "rear_engine_tail": "#ff00c8",
    "support_auxiliary": "#5668ff",
}
GENERATOR_OVERLAY_COLORS = {
    "nose_spear": "#fff2a0",
    "side_blade": "#ffe35c",
    "secondary_blade": "#ffffff",
    "rear_louvers": "#f6f2ff",
    "rear_center_glow": "#fff2a0",
    "shoulder_line": "#ffffff",
    "tail_bar": "#ffe35c",
    "mudguard_edge": "#ffffff",
}


def _source_label_maps() -> dict[str, tuple[np.ndarray, dict[str, int]]]:
    parts_dir = ROOT / "resources" / "authoritative" / "parts"
    maps: dict[str, tuple[np.ndarray, dict[str, int]]] = {}
    for name in ("psd_parts", "panels_high", "panels_fine"):
        labels = np.load(parts_dir / f"{name}_labels.npy")
        zones = json.loads((parts_dir / f"{name}.json").read_text())["zones"]
        maps[name] = (labels, {zone["name"]: int(zone["id"]) for zone in zones})
    return maps


def _catalog_target_mask(
    target: str,
    catalog: dict[str, dict[str, Any]],
    label_maps: dict[str, tuple[np.ndarray, dict[str, int]]],
) -> np.ndarray:
    panel = catalog[target]
    mask = np.zeros((SIZE, SIZE), dtype=bool)
    missing: list[str] = []
    for zone_name in panel["source_zones"]:
        found = False
        for source_map in panel["source_maps"]:
            labels, zone_ids = label_maps[source_map]
            if zone_name in zone_ids:
                mask |= labels == zone_ids[zone_name]
                found = True
                break
        if not found:
            missing.append(zone_name)
    if missing:
        raise KeyError(f"{target} references missing source zones: {missing}")
    return mask


def _family_masks(catalog: dict[str, dict[str, Any]]) -> dict[str, np.ndarray]:
    label_maps = _source_label_maps()
    family_masks: dict[str, np.ndarray] = {}
    for family_name, family in SURFACE_FAMILIES.items():
        mask = np.zeros((SIZE, SIZE), dtype=bool)
        for target in family["targets"]:
            mask |= _catalog_target_mask(target, catalog, label_maps)
        family_masks[family_name] = mask
    return family_masks


def _blend(rgb: np.ndarray, mask: np.ndarray, color: str, strength: float) -> None:
    if not mask.any():
        return
    amount = mask.astype(np.float32) * strength
    rgb[:] = rgb * (1.0 - amount[..., None]) + hx(color) * amount[..., None]


def _edge(mask: np.ndarray) -> np.ndarray:
    return binary_dilation(mask, iterations=2) & ~mask


def build_panel_probe_rgba() -> tuple[Image.Image, dict[str, Any], dict[str, Any]]:
    inventory = build_part_inventory()
    catalog = inventory["paintable_panel_catalog"]["panels"]
    fields = load_fields()
    coverage = fields["coverage"]
    panel_masks = build_stock_panel_masks(fields)

    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    alpha = np.full((SIZE, SIZE), 112, dtype=np.float32)
    rgb[coverage] = hx("#101014")

    family_masks = _family_masks(catalog)
    family_report: dict[str, Any] = {}
    for family_name in (
        "support_auxiliary",
        "side_flanks_aero",
        "cockpit_mid_deck",
        "rear_engine_tail",
        "front_nose_centerline",
    ):
        mask = family_masks[family_name] & coverage
        _blend(rgb, mask, FAMILY_COLORS[family_name], 0.78)
        alpha[mask] = np.maximum(alpha[mask], 146)

        targets = SURFACE_FAMILIES[family_name]["targets"]
        source_counts = _status_counts(catalog[target]["source_status"] for target in targets)
        runtime_counts = _status_counts(catalog[target]["tmuf_runtime_status"] for target in targets)
        family_report[family_name] = {
            "color": FAMILY_COLORS[family_name],
            "targets": list(targets),
            "pixel_count": int(mask.sum()),
            "source_status_counts": source_counts,
            "runtime_status_counts": runtime_counts,
            "source_status_summary": _format_counts(source_counts),
            "runtime_status_summary": _format_counts(runtime_counts),
            "tmuf_runtime_status": "not_proven_until_smoke",
        }

    generator_report: dict[str, Any] = {}
    for name in GENERATOR_MASKS_NOT_CATALOG_PANELS:
        panel = panel_masks[name]
        mask = panel.mask & coverage
        if name in GENERATOR_OVERLAY_COLORS:
            _blend(rgb, mask, GENERATOR_OVERLAY_COLORS[name], 0.48)
            _blend(rgb, _edge(mask) & coverage, "#ffffff", 0.62)
            alpha[mask] = np.maximum(alpha[mask], 150)
        entry = panel.report_entry()
        generator_report[name] = {
            "catalog_status": "not_catalog_panel",
            "evidence_status": entry["evidence_status"],
            "pixel_count": entry["pixel_count"],
            "risk_class": entry["risk_class"],
            "source_files": entry["source_files"],
            "source_zones": entry["source_zones"],
            "design_use": entry["design_use"],
        }

    ao_path = REF_DIR / "official_prelight_AO.png"
    if ao_path.exists():
        ao = np.asarray(Image.open(ao_path).convert("L").resize((SIZE, SIZE)), dtype=np.float32)
        rgb *= (0.78 + 0.22 * ao / 255.0)[..., None]

    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA"), family_report, generator_report


def save_outputs() -> dict[str, str]:
    out_skin = ROOT / "out" / "skins" / f"{PANEL_PROBE_NAME}.zip"
    out_atlas = ROOT / "out" / "previews" / f"{PANEL_PROBE_NAME}_atlas.png"
    out_preview = ROOT / "out" / "previews" / f"{PANEL_PROBE_NAME}_projected_side_top_rear.png"
    out_report = ROOT / "out" / "reports" / f"{PANEL_PROBE_NAME}.json"
    for path in (out_skin.parent, out_atlas.parent, out_report.parent):
        path.mkdir(parents=True, exist_ok=True)

    image, family_report, generator_report = build_panel_probe_rgba()
    icon = image.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS).convert("RGBA")
    with zipfile.ZipFile(out_skin, "w", zipfile.ZIP_DEFLATED) as zf:
        write_stable_zip_entry(zf, "Diffuse.dds", build_dds_dxt5_bytes(image, mipmaps=True))
        write_stable_zip_entry(zf, "Icon.dds", build_dds_dxt5_bytes(icon, mipmaps=True))

    image.save(out_atlas)
    fields = load_fields()
    rgba = np.asarray(image)
    side = project_view(rgba, "side", fields)
    top = project_view(rgba, "top", fields)
    rear = project_view(rgba, "rear", fields)
    pad = 14
    canvas = Image.new("RGB", (side.width + rear.width + pad * 3, side.height + top.height + pad * 3), (10, 10, 12))
    canvas.paste(side, (pad, pad))
    canvas.paste(top, (pad, pad * 2 + side.height))
    canvas.paste(rear, (pad * 2 + side.width, pad))
    canvas.save(out_preview)

    report = {
        "skin_name": PANEL_PROBE_NAME,
        "route": "stock_diffuse_only",
        "package_files": ["Diffuse.dds", "Icon.dds"],
        "tmuf_smoke_test": "not_run",
        "supplemental_smoke_artifact": True,
        "does_not_prove_tmuf_smoke": True,
        "proof_role": "panel_family_runtime_visibility_probe",
        "evidence_status": {
            "stock_diffuse_route": "proven_by_local_docs_and_package_contract",
            "gbuffer_mapping": "experimental_until_tmuf_smoke",
            "tmuf_runtime_visibility": "not_proven_until_smoke",
            "dds_package": "generated_and_header_checked_by_tests",
            "donor_gbx": "not_used",
            "details_dds": "not_used",
            "projshad_dds": "not_used",
        },
        "input_evidence": input_evidence(PREMIUM_DIFFUSE_INPUTS),
        "output_artifacts": stock_output_artifacts(out_skin, out_atlas, out_preview),
        "panel_family_colors": FAMILY_COLORS,
        "surface_families": family_report,
        "generator_masks_not_catalog_panels": generator_report,
        "known_limits": [
            "This supplemental probe does not pass the calibration gate.",
            "It helps inspect panel-family runtime visibility after loading in TMUF/TMNF.",
            "Generated and GBuffer-driven masks remain experimental until real smoke screenshots are recorded.",
        ],
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return {
        "name": PANEL_PROBE_NAME,
        "zip": str(out_skin),
        "atlas": str(out_atlas),
        "projection": str(out_preview),
        "report": str(out_report),
    }


def main() -> int:
    outputs = save_outputs()
    print(f"wrote {outputs['zip']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
