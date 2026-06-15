from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.evidence.part_inventory import ROOT, build_part_inventory


DEFAULT_JSON_OUTPUT = ROOT / "out" / "reports" / "stock_panel_deep_dive.json"
DEFAULT_MARKDOWN_OUTPUT = ROOT / "docs" / "stock_panel_deep_dive.md"

SURFACE_FAMILIES = {
    "front_nose_centerline": {
        "description": "Front identity, nose flow, splitter-like support panels, and centerline probes.",
        "targets": [
            "nose_identity_panel",
            "center_spine",
            "nose_deck_generated_panels",
            "nose_floor_generated_panels",
            "nose_side_generated_panels",
            "side_wings",
            "front_mudguard_caps",
            "front_mudguard_edge_details",
        ],
    },
    "cockpit_mid_deck": {
        "description": "Top body quadrants, cockpit-adjacent deck fields, large flank panels, and pilot harmony.",
        "targets": [
            "main_body_top_quadrants",
            "mid_deck_generated_panels",
            "mid_side_generated_panel",
            "mid_floor_generated_panels",
            "helmet_and_visor",
            "side_vent_inside",
        ],
    },
    "side_flanks_aero": {
        "description": "Sidepod blades, side winglets, mirrors, vents, and side-to-tail color rhythm.",
        "targets": [
            "sidepod_blades",
            "mid_side_generated_panel",
            "rear_side_generated_panels",
            "side_wings",
            "mirrors_and_holders",
            "side_vent_inside",
            "tailwing_bands",
        ],
    },
    "rear_engine_tail": {
        "description": "Rear deck, louver rows, tailwing bands, rear guard rhythm, and lower rear support panels.",
        "targets": [
            "engine_rear_deck",
            "rear_deck_fine_louver_rows",
            "rear_side_generated_panels",
            "rear_floor_generated_panels",
            "tailwing_bands",
            "rear_mudguard_caps",
            "rear_mudguard_edge_details",
        ],
    },
    "support_auxiliary": {
        "description": "Non-hero support surfaces that can polish a skin without proving custom materials.",
        "targets": [
            "underbody_dark",
            "licence_plate_blocks",
            "rear_wheel_diffuse_blocks",
            "helmet_and_visor",
            "mirrors_and_holders",
        ],
    },
}

MORE_PANEL_OPPORTUNITIES = [
    {
        "target": "mid_deck_generated_panels",
        "why_it_matters": "large cockpit and roof-flow deck fields for symmetric extra panels near the engine cover.",
    },
    {
        "target": "mid_side_generated_panel",
        "why_it_matters": "very large flank field for broad side blades and blank sponsor-like geometry without text.",
    },
    {
        "target": "rear_deck_fine_louver_rows",
        "why_it_matters": "fine rear deck rows for technical louver rhythm and paired glow accents.",
    },
    {
        "target": "nose_floor_generated_panels",
        "why_it_matters": "front floor returns for splitter-like lower wedge continuation probes.",
    },
    {
        "target": "rear_floor_generated_panels",
        "why_it_matters": "low rear support blocks for shadow fields and tail color echoes.",
    },
]

PANEL_ALIASES = {
    "front_splitter_floor_probe": "nose_floor_generated_panels",
    "front_winglet_panels": "side_wings",
    "upper_center_roof_spine": "center_spine + main_body_top_quadrants",
    "nose_top_deck_panels": "nose_deck_generated_panels",
    "engine_louver_rows": "rear_deck_fine_louver_rows",
    "large_side_flank_panel": "mid_side_generated_panel",
}


def build_panel_deep_dive(base_dir: Path = ROOT) -> dict[str, Any]:
    base_dir = base_dir.resolve()
    inventory = build_part_inventory(base_dir)
    catalog = inventory["paintable_panel_catalog"]["panels"]
    candidate_usage = _candidate_usage(base_dir / "out" / "reports")

    surface_families = {
        family_name: _family_entry(family_name, family, catalog, candidate_usage)
        for family_name, family in SURFACE_FAMILIES.items()
    }

    opportunities = []
    for opportunity in MORE_PANEL_OPPORTUNITIES:
        target = opportunity["target"]
        panel = catalog[target]
        opportunities.append(
            {
                "target": target,
                "why_it_matters": opportunity["why_it_matters"],
                "source_status": panel["source_status"],
                "tmuf_runtime_status": panel["tmuf_runtime_status"],
                "total_label_area": panel["total_label_area"],
                "source_zones": panel["source_zones"],
                "candidate_usage": candidate_usage.get(target, []),
                "proof_gates": [
                    "run TMUF smoke calibration before treating GBuffer/generated placement as runtime truth",
                    "capture front/side/rear/top screenshots before promoting visual claims",
                ],
            }
        )

    return {
        "schema": "tmuf_premium_skin_lab.stock_panel_deep_dive.v1",
        "source_inventory": "out/reports/stock_part_inventory.json",
        "source_inventory_schema": inventory["schema"],
        "catalog_target_count": len(catalog),
        "label_map_counts": {
            name: label_map["zone_count"]
            for name, label_map in inventory["label_maps"].items()
        },
        "evidence_boundary": {
            "stock_package_route": "stock_diffuse_only",
            "tmuf_runtime_status": "not_proven_until_smoke",
            "local_label_maps": "proven local atlas evidence",
            "gbuffer": inventory["evidence_status"]["gbuffer"],
            "known_limits": [
                "no roof named PSD zone",
                "no DDS orientation claim until TMUF smoke",
                "no UV seam quality claim until TMUF smoke",
                "no material gloss claim from Diffuse alpha until TMUF smoke",
                "generated panel names provide token evidence only",
            ],
        },
        "surface_families": surface_families,
        "panel_aliases": PANEL_ALIASES,
        "candidate_usage_by_target": candidate_usage,
        "more_panel_opportunities": opportunities,
        "locked_or_non_stock_routes": _locked_routes(),
    }


def write_panel_deep_dive(
    *,
    json_output: Path = DEFAULT_JSON_OUTPUT,
    markdown_output: Path = DEFAULT_MARKDOWN_OUTPUT,
    base_dir: Path = ROOT,
) -> dict[str, Path]:
    report = build_panel_deep_dive(base_dir)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    markdown_output.write_text(render_panel_deep_dive_markdown(report))
    return {"json_output": json_output, "markdown_output": markdown_output}


def render_panel_deep_dive_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Stock Panel Deep Dive",
        "",
        "This is generated from the stock part inventory and candidate reports. It is evidence for local atlas targeting, not proof of TMUF runtime visibility.",
        "",
        "## Evidence Boundary",
        "",
        f"- Stock route: `{report['evidence_boundary']['stock_package_route']}`.",
        f"- TMUF runtime status: `{report['evidence_boundary']['tmuf_runtime_status']}`.",
        f"- Catalog targets: `{report['catalog_target_count']}`.",
        f"- Label maps: `psd_parts={report['label_map_counts']['psd_parts']}`, `panels_high={report['label_map_counts']['panels_high']}`, `panels_fine={report['label_map_counts']['panels_fine']}`.",
        "",
        "Known limits:",
    ]
    lines.extend(f"- {limit}." for limit in report["evidence_boundary"]["known_limits"])

    lines.extend(["", "## Surface Families", ""])
    for family_name, family in report["surface_families"].items():
        lines.extend(
            [
                f"### {family_name}",
                "",
                family["description"],
                "",
                "| Target | Status | Area | Use |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for entry in family["target_entries"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{entry['target']}`",
                        f"`{entry['source_status']}`",
                        str(entry["total_label_area"]),
                        entry["design_role"],
                    ]
                )
                + " |"
            )
        lines.append("")

    lines.extend(
        [
            "## More Panel Opportunities",
            "",
            "| Target | Current candidates | Why it matters |",
            "| --- | --- | --- |",
        ]
    )
    for opportunity in report["more_panel_opportunities"]:
        usage = ", ".join(opportunity["candidate_usage"]) or "none yet"
        lines.append(
            f"| `{opportunity['target']}` | {usage} | {opportunity['why_it_matters']} |"
        )

    lines.extend(["", "## Aliases", ""])
    for alias, target in report["panel_aliases"].items():
        lines.append(f"- `{alias}` -> `{target}`")

    lines.extend(
        [
            "",
            "## Locked Or Non-Stock Routes",
            "",
            "| Route | Status | Why locked |",
            "| --- | --- | --- |",
        ]
    )
    for route in report["locked_or_non_stock_routes"]:
        notes = "; ".join(route["notes"])
        display = route["display"]
        lines.append(f"| `{display}` | `{route['status']}` | {notes} |")

    return "\n".join(lines) + "\n"


def _family_entry(
    family_name: str,
    family: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
    candidate_usage: dict[str, list[str]],
) -> dict[str, Any]:
    missing = [target for target in family["targets"] if target not in catalog]
    if missing:
        raise KeyError(f"{family_name} references missing catalog targets: {', '.join(missing)}")

    target_entries = [
        _target_entry(target, catalog[target], candidate_usage.get(target, []))
        for target in family["targets"]
    ]
    return {
        "description": family["description"],
        "targets": list(family["targets"]),
        "target_count": len(family["targets"]),
        "total_label_area": int(sum(entry["total_label_area"] for entry in target_entries)),
        "source_statuses": sorted({entry["source_status"] for entry in target_entries}),
        "target_entries": target_entries,
    }


def _target_entry(target: str, panel: dict[str, Any], candidate_usage: list[str]) -> dict[str, Any]:
    return {
        "target": target,
        "source_status": panel["source_status"],
        "tmuf_runtime_status": panel["tmuf_runtime_status"],
        "source_maps": panel["source_maps"],
        "source_zones": panel["source_zones"],
        "total_label_area": panel["total_label_area"],
        "risk_classes": panel["risk_classes"],
        "safe_design_scale": panel["safe_design_scale"],
        "design_role": panel["design_role"],
        "symmetry_policy": panel["symmetry_policy"],
        "geometry_constraints": panel["geometry_constraints"],
        "proof_notes": panel["proof_notes"],
        "candidate_usage": candidate_usage,
    }


def _candidate_usage(reports_dir: Path) -> dict[str, list[str]]:
    usage: dict[str, list[str]] = {}
    if not reports_dir.exists():
        return usage

    for path in sorted(reports_dir.glob("*.json")):
        data = json.loads(path.read_text())
        targets = data.get("panel_catalog_targets")
        if not targets:
            continue
        candidate_name = data.get("candidate", path.stem)
        for target in targets:
            usage.setdefault(target, []).append(candidate_name)
    return {target: sorted(candidates) for target, candidates in sorted(usage.items())}


def _locked_routes() -> list[dict[str, Any]]:
    return [
        {
            "route": "details_dds",
            "display": "Details.dds",
            "status": "locked_custom_profile",
            "source_files": ["src/profiles/gates.py", "resources/evidence_manifest.json"],
            "notes": [
                "not stock_diffuse_only",
                "belongs behind the CH_2026 full-car proof gate",
                "does not prove tyre sidewall, tread, hub material, or stock wheel routing",
            ],
            "proof_gates": [
                "stock_calibration_tmuf_smoke_passed",
                "ch2026_fullcar_package_build_report",
                "ch2026_fullcar_tmuf_smoke_passed",
            ],
        },
        {
            "route": "projshad_dds",
            "display": "ProjShad.dds",
            "status": "locked_custom_profile",
            "source_files": ["src/profiles/gates.py", "resources/experimental/flows/canvas_compose/composer.py"],
            "notes": [
                "not stock_diffuse_only",
                "optional underglow/shadow route only after CH_2026 full-car proof",
            ],
            "proof_gates": [
                "stock_calibration_tmuf_smoke_passed",
                "ch2026_fullcar_tmuf_smoke_passed",
            ],
        },
        {
            "route": "custom_mesh_nomud",
            "display": "custom mesh / no mudguard",
            "status": "locked_custom_profile",
            "source_files": [
                "resources/experimental/base_car/CH_2026_NOT_STOCK_STADIUM_DETAILS_CUSTOM_MESH.zip",
                "resources/experimental/flows/remove_guards",
                "src/profiles/gates.py",
            ],
            "notes": [
                "not stock_diffuse_only",
                "custom GBX and no-mudguard work cannot be used in the stock generator",
            ],
            "proof_gates": [
                "CH_2026 full-car package build report",
                "CH_2026 full-car TMUF smoke passed",
                "nomud package build report",
                "nomud TMUF smoke passed",
            ],
        },
    ]
