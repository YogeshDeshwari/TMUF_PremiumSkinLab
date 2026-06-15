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


def _source_files_for_panel(source_maps: list[str], *, include_gbuffer: bool) -> list[str]:
    files: list[str] = []
    for source_map in source_maps:
        files.append(f"resources/authoritative/parts/{source_map}.json")
        files.append(f"resources/authoritative/parts/{source_map}_labels.npy")
    if include_gbuffer:
        files.extend(
            [
                "resources/authoritative/gbuffer/position_2048.npy",
                "resources/authoritative/gbuffer/coverage_2048.npy",
                "resources/authoritative/gbuffer/extents_2048.json",
            ]
        )
    return files


def _catalog_panel(
    *,
    name: str,
    source_status: str,
    source_maps: list[str],
    source_zones: list[str],
    design_role: str,
    safe_design_scale: str,
    geometry_constraints: list[str],
    proof_notes: list[str],
    label_maps: dict[str, dict[str, Any]],
    include_gbuffer: bool = False,
) -> dict[str, Any]:
    zone_indexes = {
        source_map: {zone["name"]: zone for zone in label_maps[source_map]["zones"]}
        for source_map in source_maps
    }
    matched: list[dict[str, Any]] = []
    missing: list[str] = []
    for zone_name in source_zones:
        for source_map, zone_index in zone_indexes.items():
            if zone_name in zone_index:
                zone = zone_index[zone_name]
                matched.append(
                    {
                        "map": source_map,
                        "name": zone["name"],
                        "area": zone["area"],
                        "bbox": zone["bbox"],
                        "risk_class": zone["risk_class"],
                    }
                )
                break
        else:
            missing.append(zone_name)

    if missing:
        raise KeyError(f"{name} references missing panel zones: {', '.join(missing)}")

    return {
        "source_status": source_status,
        "tmuf_runtime_status": "not_proven_until_smoke",
        "source_files": _source_files_for_panel(source_maps, include_gbuffer=include_gbuffer),
        "source_maps": source_maps,
        "source_zones": source_zones,
        "zone_evidence": matched,
        "total_label_area": int(sum(zone["area"] for zone in matched)),
        "risk_classes": sorted({zone["risk_class"] for zone in matched}),
        "design_role": design_role,
        "safe_design_scale": safe_design_scale,
        "geometry_constraints": geometry_constraints,
        "proof_notes": proof_notes,
    }


def _paintable_panel_catalog(label_maps: dict[str, dict[str, Any]]) -> dict[str, Any]:
    panels = {
        "main_body_top_quadrants": _catalog_panel(
            name="main_body_top_quadrants",
            source_status="proven_local_label_map",
            source_maps=["psd_parts"],
            source_zones=["MainBodyTOP_TL", "MainBodyTOP_TR", "MainBodyTOP_BL", "MainBodyTOP_BR"],
            design_role="large base fields, hard-edge blocks, long stripe clipping, and broad abstract panels",
            safe_design_scale="broad_identity_surface",
            geometry_constraints=["named PSD quadrants only"],
            proof_notes=["local atlas labels are proven; TMUF runtime visibility still requires calibration smoke"],
            label_maps=label_maps,
        ),
        "nose_identity_panel": _catalog_panel(
            name="nose_identity_panel",
            source_status="proven_local_label_map",
            source_maps=["psd_parts"],
            source_zones=["NosePart"],
            design_role="front identity wedge, spear tip, and number-free badge field",
            safe_design_scale="broad_identity_surface",
            geometry_constraints=["named PSD nose zone only"],
            proof_notes=["local NosePart label is proven; front direction confirmation still belongs to smoke calibration"],
            label_maps=label_maps,
        ),
        "center_spine": _catalog_panel(
            name="center_spine",
            source_status="experimental_until_tmuf_smoke",
            source_maps=["psd_parts"],
            source_zones=["MainBodyTOP_TL", "MainBodyTOP_TR", "MainBodyTOP_BL", "MainBodyTOP_BR"],
            design_role="long center stripe, symmetry probe, and top-flow alignment",
            safe_design_scale="medium_to_broad_accent",
            geometry_constraints=["LAT/X symmetry", "LEN/Z flow", "HGT/Y upper surfaces"],
            proof_notes=["GBuffer centerline placement remains experimental until TMUF smoke"],
            label_maps=label_maps,
            include_gbuffer=True,
        ),
        "sidepod_blades": _catalog_panel(
            name="sidepod_blades",
            source_status="mixed_local_label_and_experimental_gbuffer",
            source_maps=["psd_parts"],
            source_zones=["SideUnderColor_L", "SideUnderColor_R"],
            design_role="lower side sweeps, sponsor-like blank blocks, and side color returns",
            safe_design_scale="broad_identity_surface",
            geometry_constraints=["LAT/X side split", "HGT/Y lower side band", "LEN/Z flow"],
            proof_notes=["SideUnderColor labels are proven; 3D blade placement remains experimental until TMUF smoke"],
            label_maps=label_maps,
            include_gbuffer=True,
        ),
        "engine_rear_deck": _catalog_panel(
            name="engine_rear_deck",
            source_status="mixed_generated_labels_and_experimental_gbuffer",
            source_maps=["panels_high", "panels_fine"],
            source_zones=["rear_deck_C_63", "rear_deck_C_08", "rear_deck_C_21", "rear_deck_C_140"],
            design_role="rear deck louvers, glow blocks, technical vent rhythm, and symmetric rear highlights",
            safe_design_scale="medium_to_broad_accent",
            geometry_constraints=["low LEN/Z", "high HGT/Y", "LAT/X mirrored offset bands"],
            proof_notes=[
                "generated panel names support only deck/rear token evidence",
                "exact TMUF visual interpretation and louver placement remain experimental until smoke",
            ],
            label_maps=label_maps,
            include_gbuffer=True,
        ),
        "tailwing_bands": _catalog_panel(
            name="tailwing_bands",
            source_status="proven_local_label_map",
            source_maps=["psd_parts"],
            source_zones=["Tailwing_L", "Tailwing_R", "TailWingUnderBorderColor"],
            design_role="rear wing bands, edge trim, and high-contrast rear identity",
            safe_design_scale="medium_to_broad_accent",
            geometry_constraints=["named PSD tailwing zones only"],
            proof_notes=["tailwing labels are proven local atlas evidence; runtime visibility still requires smoke"],
            label_maps=label_maps,
        ),
        "front_mudguard_caps": _catalog_panel(
            name="front_mudguard_caps",
            source_status="mixed_local_label_and_experimental_gbuffer",
            source_maps=["psd_parts"],
            source_zones=["FrontMudGuards", "FrontMudguards.Inside", "FrontMudguardUnderColor", "FrontMudguardEdgeColor"],
            design_role="front guard caps, edge highlights, and calibration-visible color checks",
            safe_design_scale="medium_to_broad_accent",
            geometry_constraints=["named PSD mudguard labels", "LEN/Z front split"],
            proof_notes=["LEN/Z front split remains experimental until TMUF smoke"],
            label_maps=label_maps,
            include_gbuffer=True,
        ),
        "rear_mudguard_caps": _catalog_panel(
            name="rear_mudguard_caps",
            source_status="mixed_local_label_and_experimental_gbuffer",
            source_maps=["psd_parts"],
            source_zones=["RearMudGuards", "RearMudGuardsInside", "RearMudguardUnderColor", "RearMudguardsTip", "RearMudguardsedgeColor"],
            design_role="rear guard caps, rear color echo, and wheel-arch rhythm",
            safe_design_scale="medium_to_broad_accent",
            geometry_constraints=["named PSD mudguard labels", "LEN/Z rear split"],
            proof_notes=["LEN/Z rear split remains experimental until TMUF smoke"],
            label_maps=label_maps,
            include_gbuffer=True,
        ),
        "side_wings": _catalog_panel(
            name="side_wings",
            source_status="proven_local_label_map",
            source_maps=["psd_parts"],
            source_zones=["SIdeWings", "SideWingsUNDER"],
            design_role="small aero flicks and secondary color hits",
            safe_design_scale="medium_accent_surface",
            geometry_constraints=["named PSD side wing zones only"],
            proof_notes=["local labels are proven; visibility and seam quality still require TMUF review"],
            label_maps=label_maps,
        ),
        "mirrors_and_holders": _catalog_panel(
            name="mirrors_and_holders",
            source_status="proven_local_label_map",
            source_maps=["psd_parts"],
            source_zones=["SideMirrors", "MirrorHolders"],
            design_role="small contrast checks and polished micro-detail",
            safe_design_scale="small_detail_surface",
            geometry_constraints=["named PSD mirror zones only"],
            proof_notes=["small details can disappear in game; use for probe and restraint until visual acceptance"],
            label_maps=label_maps,
        ),
        "helmet_and_visor": _catalog_panel(
            name="helmet_and_visor",
            source_status="proven_local_label_map",
            source_maps=["psd_parts"],
            source_zones=["Helmet_TL", "Helmet_TR", "Helmet_BL", "Helmet_BR", "HelmetGlass_L", "HelmetGlass_R"],
            design_role="driver color harmony and restrained glass/visor shading",
            safe_design_scale="medium_accent_surface",
            geometry_constraints=["named PSD helmet and glass zones only"],
            proof_notes=["helmet is visible local atlas evidence but should not drive main car identity"],
            label_maps=label_maps,
        ),
        "underbody_dark": _catalog_panel(
            name="underbody_dark",
            source_status="proven_local_label_map",
            source_maps=["psd_parts"],
            source_zones=[
                "MainBodyUNDER_TL",
                "MainBodyUNDER_TR",
                "MainBodyUNDER_BL",
                "MainBodyUNDER_BR",
                "UnderPlate_L",
                "UnderPlate_R",
                "UnderPlate.insidecolor :)",
            ],
            design_role="dark material continuity, low reflections, and non-hero shadow fields",
            safe_design_scale="broad_support_surface",
            geometry_constraints=["named PSD underside and underplate zones only"],
            proof_notes=["use as support material; not a proof of wheel, tyre, Details.dds, or ProjShad behavior"],
            label_maps=label_maps,
        ),
    }
    return {
        "schema": "tmuf_premium_skin_lab.paintable_panel_catalog.v1",
        "tmuf_runtime_status": "not_proven_until_smoke",
        "boundary": [
            "no panel entry proves TMUF runtime visibility before calibration smoke",
            "local label maps prove atlas regions, not in-game seam quality",
            "GBuffer-derived constraints remain experimental_until_tmuf_smoke",
            "generated panel names provide token evidence only, not stock semantic truth beyond their local labels",
        ],
        "panels": panels,
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
        "paintable_panel_catalog": _paintable_panel_catalog(label_maps),
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
