from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
PARTS_DIR = ROOT / "resources" / "authoritative" / "parts"
GBUFFER_DIR = ROOT / "resources" / "authoritative" / "gbuffer"
MESH_DIR = ROOT / "resources" / "authoritative" / "mesh"


def _risk_class(area: int) -> str:
    if area >= 100_000:
        return "broad_design_surface"
    if area >= 25_000:
        return "medium_accent_surface"
    if area >= 5_000:
        return "small_detail_surface"
    return "probe_only_tiny_fragment"


def _psd_group(name: str) -> str:
    lowered = name.lower()
    if "mainbodytop" in lowered:
        return "main_body_top"
    if "mainbodyunder" in lowered:
        return "main_body_under"
    if "helmetglass" in lowered:
        return "helmet_glass"
    if "helmet" in lowered:
        return "helmet"
    if "mudguard" in lowered:
        return "mudguards"
    if "sideundercolor" in lowered:
        return "side_under_color"
    if "tailwing" in lowered:
        return "tailwing"
    if "sidewing" in lowered:
        return "side_wings"
    if "underplate" in lowered:
        return "underplate"
    if "nose" in lowered:
        return "nose"
    if "licence" in lowered:
        return "licence_plate"
    if "wheel" in lowered or "knob" in lowered:
        return "wheel_blocks"
    if "mirror" in lowered:
        return "mirrors"
    return lowered.replace(" ", "_")


def _panel_group(name: str) -> str:
    parts = name.split("_")
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return parts[0]


def _zone_entry(zone: dict[str, Any], group: str) -> dict[str, Any]:
    area = int(zone["area"])
    return {
        "id": int(zone["id"]),
        "name": zone["name"],
        "group": group,
        "area": area,
        "bbox": [int(value) for value in zone["bbox"]],
        "centroid": [round(float(value), 6) for value in zone["centroid"]],
        "risk_class": _risk_class(area),
    }


def _summarize_groups(zones: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for zone in zones:
        group = groups.setdefault(zone["group"], {"zone_count": 0, "total_area": 0, "zones": []})
        group["zone_count"] += 1
        group["total_area"] += zone["area"]
        group["zones"].append(zone["name"])
    for group in groups.values():
        group["zones"] = sorted(group["zones"])
    return dict(sorted(groups.items()))


def _label_map_summary(name: str, *, base_dir: Path) -> dict[str, Any]:
    json_path = base_dir / "resources" / "authoritative" / "parts" / f"{name}.json"
    labels_path = base_dir / "resources" / "authoritative" / "parts" / f"{name}_labels.npy"
    data = json.loads(json_path.read_text())
    labels = np.load(labels_path)

    group_fn = _psd_group if name == "psd_parts" else _panel_group
    zones = [_zone_entry(zone, group_fn(zone["name"])) for zone in data["zones"]]

    json_ids = {zone["id"] for zone in zones}
    label_ids = {int(value) for value in np.unique(labels) if int(value) > 0}
    atlas_pixels = int(labels.shape[0] * labels.shape[1])
    nonzero_pixels = int(np.count_nonzero(labels))

    return {
        "source_json": str(json_path.relative_to(base_dir)),
        "source_labels": str(labels_path.relative_to(base_dir)),
        "size": int(data["size"]),
        "shape": [int(value) for value in labels.shape],
        "dtype": str(labels.dtype),
        "zone_count": len(zones),
        "nonzero_pixels": nonzero_pixels,
        "atlas_coverage_ratio": round(nonzero_pixels / atlas_pixels, 6),
        "json_ids_match_label_map_ids": json_ids == label_ids,
        "json_ids_missing_from_labels": sorted(json_ids - label_ids),
        "label_ids_missing_from_json": sorted(label_ids - json_ids),
        "groups": _summarize_groups(zones),
        "zones": sorted(zones, key=lambda zone: (-zone["area"], zone["name"])),
    }


def _axis_summary(values: np.ndarray) -> dict[str, Any]:
    return {
        "min": round(float(values.min()), 9),
        "max": round(float(values.max()), 9),
        "q05": round(float(np.quantile(values, 0.05)), 6),
        "q25": round(float(np.quantile(values, 0.25)), 6),
        "q50": round(float(np.quantile(values, 0.50)), 6),
        "q75": round(float(np.quantile(values, 0.75)), 6),
        "q95": round(float(np.quantile(values, 0.95)), 6),
    }


def _gbuffer_summary(*, base_dir: Path) -> dict[str, Any]:
    gbuffer_dir = base_dir / "resources" / "authoritative" / "gbuffer"
    extents = json.loads((gbuffer_dir / "extents_2048.json").read_text())
    coverage = np.load(gbuffer_dir / "coverage_2048.npy")
    position = np.load(gbuffer_dir / "position_2048.npy")
    covered = coverage > 0

    axis_roles = {key: int(value) for key, value in extents["axis_roles"].items()}
    normalized_axes = {
        role: _axis_summary(position[..., axis][covered])
        for role, axis in axis_roles.items()
    }

    return {
        "source_extents": "resources/authoritative/gbuffer/extents_2048.json",
        "source_coverage": "resources/authoritative/gbuffer/coverage_2048.npy",
        "source_position": "resources/authoritative/gbuffer/position_2048.npy",
        "status": "experimental_until_tmuf_smoke",
        "axis_roles": axis_roles,
        "mesh_space_extents": {
            "min": [round(float(value), 9) for value in extents["min"]],
            "max": [round(float(value), 9) for value in extents["max"]],
            "span": [round(float(value), 9) for value in extents["span"]],
        },
        "coverage_shape": [int(value) for value in coverage.shape],
        "coverage_values": [int(value) for value in sorted(np.unique(coverage))],
        "covered_pixels": int(covered.sum()),
        "background_pixels": int((~covered).sum()),
        "normalized_axis_quantiles": normalized_axes,
    }


def _parse_obj(path: Path) -> dict[str, Any]:
    vertices: list[list[float]] = []
    uvs: list[list[float]] = []
    normal_count = 0
    face_count = 0
    faces_with_missing_uv = 0

    for line in path.read_text(errors="ignore").splitlines():
        if line.startswith("v "):
            _tag, x, y, z, *_rest = line.split()
            vertices.append([float(x), float(y), float(z)])
        elif line.startswith("vt "):
            _tag, u, v, *_rest = line.split()
            uvs.append([float(u), float(v)])
        elif line.startswith("vn "):
            normal_count += 1
        elif line.startswith("f "):
            face_count += 1
            for item in line.split()[1:]:
                parts = item.split("/")
                if len(parts) < 2 or not parts[1]:
                    faces_with_missing_uv += 1
                    break

    vertex_array = np.asarray(vertices, dtype=np.float64)
    uv_array = np.asarray(uvs, dtype=np.float64)
    role = "unknown"
    lowered = path.name.lower()
    if "body" in lowered:
        role = "body"
    elif "guard" in lowered:
        role = "mudguard"
    elif "hub" in lowered:
        role = "hub"
    elif "pilhead" in lowered:
        role = "pilot_head"
    elif "fixed" in lowered:
        role = "fixed"

    return {
        "path": str(path.relative_to(ROOT)),
        "role": role,
        "vertex_count": len(vertices),
        "uv_count": len(uvs),
        "normal_count": normal_count,
        "face_count": face_count,
        "faces_with_missing_uv": faces_with_missing_uv,
        "xyz_min": [round(float(value), 9) for value in vertex_array.min(axis=0)],
        "xyz_max": [round(float(value), 9) for value in vertex_array.max(axis=0)],
        "uv_min": [round(float(value), 9) for value in uv_array.min(axis=0)],
        "uv_max": [round(float(value), 9) for value in uv_array.max(axis=0)],
    }


def _mesh_summary(*, base_dir: Path) -> dict[str, Any]:
    mesh_dir = base_dir / "resources" / "authoritative" / "mesh"
    components = [_parse_obj(path) for path in sorted(mesh_dir.glob("*.obj"))]

    xyz_min = np.asarray([component["xyz_min"] for component in components], dtype=np.float64).min(axis=0)
    xyz_max = np.asarray([component["xyz_max"] for component in components], dtype=np.float64).max(axis=0)
    return {
        "source_dir": "resources/authoritative/mesh",
        "component_count": len(components),
        "all_faces_have_uvs": all(component["faces_with_missing_uv"] == 0 for component in components),
        "aggregate_xyz_min": [round(float(value), 9) for value in xyz_min],
        "aggregate_xyz_max": [round(float(value), 9) for value in xyz_max],
        "components": components,
    }


def build_part_inventory(base_dir: Path = ROOT) -> dict[str, Any]:
    base_dir = base_dir.resolve()
    label_maps = {
        name: _label_map_summary(name, base_dir=base_dir)
        for name in ("psd_parts", "panels_high", "panels_fine")
    }

    return {
        "schema": "tmuf_premium_skin_lab.stock_part_inventory.v1",
        "evidence_status": {
            "psd_parts": "proven_local_label_map",
            "panels_high": "proven_local_label_map_generated_names",
            "panels_fine": "proven_local_label_map_generated_names",
            "mesh_objs": "proven_local_mesh_exports",
            "gbuffer": "experimental_until_tmuf_smoke",
            "tmuf_runtime_visibility": "not_proven_until_smoke",
        },
        "label_maps": label_maps,
        "gbuffer": _gbuffer_summary(base_dir=base_dir),
        "mesh": _mesh_summary(base_dir=base_dir),
        "targetable_regions": {
            "front_nose_len_positive": {
                "evidence": "LEN/Z positive end is front; front guards span Z about 1.548..2.045 and body/fixed reaches about 2.135.",
                "status": "experimental_until_tmuf_smoke_when_used_for_texture_projection",
            },
            "rear_deck_candidate_len_negative_high_hgt": {
                "evidence": "Body/fixed reach LEN/Z about -1.770 and HGT/Y about 1.056; exact semantic rear deck is not named by mesh files.",
                "status": "experimental_until_tmuf_smoke",
            },
            "left_right_sides_lat_sign": {
                "evidence": "Local L components have positive X/LAT and local R components have negative X/LAT in OBJ bounds.",
                "status": "local_mesh_evidence",
            },
            "mudguards_by_name_and_label": {
                "evidence": "Mudguard OBJs and psd_parts names separately identify guard surfaces.",
                "status": "local_mesh_and_label_evidence",
            },
            "high_low_surfaces_hgt": {
                "evidence": "GBuffer axis_roles maps HGT to axis 1/Y, with mesh HGT span about 0.147..1.056.",
                "status": "experimental_until_tmuf_smoke_when_used_for_texture_projection",
            },
        },
        "unknowns": [
            "no_tmuf_runtime_visibility_claim",
            "no_dds_orientation_claim_until_smoke",
            "no_uv_seam_quality_claim_until_smoke",
            "no_fine_panel_semantics_beyond_local_name_tokens",
            "no_material_gloss_claim_from_diffuse_alpha_until_smoke",
        ],
    }
