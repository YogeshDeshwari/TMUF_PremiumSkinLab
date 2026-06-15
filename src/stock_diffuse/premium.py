from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, gaussian_filter

from src.dds.tmnf_dds import build_dds_dxt5_bytes
from src.evidence.artifact_trace import artifact_entry, stock_output_artifacts
from src.evidence.input_trace import PREMIUM_DIFFUSE_INPUTS, input_evidence
from src.evidence.panel_visual_coverage import build_panel_visual_coverage
from src.evidence.reference_style_guidance import (
    DEFAULT_GUIDANCE,
    DEFAULT_REFERENCE_INDEX,
    build_reference_style_guidance,
    guidance_report_block,
    write_reference_style_guidance,
)
from src.stock_diffuse.calibration import SIZE, hx, load_fields, project_view
from src.stock_diffuse.package import write_stable_zip_entry
from src.stock_diffuse.panel_masks import PremiumMaskParams, build_stock_panel_masks, mask_report_entries


ROOT = Path(__file__).resolve().parents[2]
REF_DIR = ROOT / "resources" / "authoritative" / "reference"
BATCH_INDEX = ROOT / "out" / "reports" / "premium_batch_index.json"
REVIEW_BOARD = ROOT / "out" / "previews" / "premium_candidate_review_board.png"
CANDIDATE_NAMES = [
    "black_magenta_cyan_blade",
    "black_cyan_spine",
    "violet_cyber_flow",
    "dark_neon_louver",
    "magenta_cyan_race_proto",
    "black_red_cyber_minimal",
    "carbon_gold_circuit",
    "teal_magenta_vector",
    "shadow_magenta_split",
    "white_cyan_nightcore",
    "monochrome_magenta_pinstripe",
    "cyan_white_gt_block",
    "neon_checker_tail",
    "asym_diagonal_sash",
    "guard_halo_cyan",
    "full_panel_cyber_flood",
    "mint_purple_split",
    "orange_teal_circuit",
    "white_magenta_rally_blocks",
    "crimson_cyan_arrow",
]
PREMIUM_MASK_NAMES = [
    "center_spine",
    "nose_spear",
    "side_blade",
    "secondary_blade",
    "rear_louvers",
    "rear_center_glow",
    "shoulder_line",
    "tail_bar",
    "mudguards",
    "mudguard_edge",
    "tailwing",
    "side_wings",
    "mirrors",
    "underplate",
    "main_body_under",
]
PANEL_FAMILY_MASK_NAMES = [
    "nose_deck_generated_panels",
    "nose_floor_generated_panels",
    "nose_side_generated_panels",
    "mid_deck_generated_panels",
    "mid_side_generated_panel",
    "mid_floor_generated_panels",
    "rear_side_generated_panels",
    "rear_floor_generated_panels",
    "rear_deck_fine_louver_rows",
]
PREMIUM_MASK_NAMES = [*PREMIUM_MASK_NAMES, *PANEL_FAMILY_MASK_NAMES]
PANEL_CATALOG_TARGETS = [
    "tailwing_bands",
    "side_wings",
    "mirrors_and_holders",
    "underbody_dark",
]
DEFAULT_PANEL_CATALOG_TARGETS = tuple(PANEL_CATALOG_TARGETS)


@dataclass(frozen=True)
class Candidate:
    name: str
    lane_id: str
    composition_focus: str
    distinctive_masks: tuple[str, ...]
    base: str
    base2: str
    primary: str
    secondary: str
    highlight: str
    spine_width: float
    blade_slope: float
    blade_offset: float
    rear_louver_count: float
    mudguard_mode: str
    panel_catalog_targets: tuple[str, ...]
    mask_strengths: tuple[tuple[str, float], ...]

    @property
    def graphic_archetype(self) -> str:
        return LANE_GRAPHIC_ARCHETYPES.get(self.lane_id, "balanced_neon")

    @property
    def base_mask_strength(self) -> float:
        return LANE_BASE_MASK_STRENGTHS.get(self.lane_id, 0.18)


CANDIDATES = [
    Candidate(
        "black_magenta_cyan_blade",
        "side_blade_sweep",
        "wide lower side blades with a magenta nose spear and cyan side energy",
        ("side_blade", "secondary_blade", "nose_spear", "mudguard_edge"),
        "#050507",
        "#161820",
        "#ff00b8",
        "#00d8ff",
        "#f6f2ff",
        0.050,
        0.42,
        0.16,
        16.0,
        "primary_front",
        (
            "sidepod_blades",
            "nose_identity_panel",
            "nose_side_generated_panels",
            "nose_deck_generated_panels",
            "nose_floor_generated_panels",
            "front_mudguard_caps",
            "front_mudguard_edge_details",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("side_blade", 1.32),
            ("secondary_blade", 1.18),
            ("nose_spear", 1.16),
            ("mudguard_edge", 1.20),
            ("rear_louvers", 0.62),
            ("rear_center_glow", 0.76),
        ),
    ),
    Candidate(
        "black_cyan_spine",
        "center_spine_focus",
        "dominant cyan center spine with magenta guard and tail echoes",
        ("center_spine", "nose_spear", "tailwing", "mudguard_edge"),
        "#040608",
        "#111a1f",
        "#00d8ff",
        "#ff25c8",
        "#edf8ff",
        0.064,
        0.35,
        0.21,
        18.0,
        "secondary_front",
        (
            "center_spine",
            "nose_identity_panel",
            "mid_deck_generated_panels",
            "tailwing_bands",
            "front_mudguard_caps",
            "rear_mudguard_caps",
            "rear_mudguard_edge_details",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("center_spine", 1.34),
            ("nose_spear", 1.14),
            ("tailwing", 1.18),
            ("mudguard_edge", 1.12),
            ("side_blade", 0.58),
            ("secondary_blade", 0.62),
        ),
    ),
    Candidate(
        "violet_cyber_flow",
        "split_guard_flow",
        "violet/magenta flow with split guard color and cyan side structure",
        ("mudguards", "side_blade", "rear_center_glow", "tailwing"),
        "#07050b",
        "#17101d",
        "#d600ff",
        "#00e0ff",
        "#fff5ff",
        0.044,
        0.50,
        0.13,
        14.0,
        "split",
        (
            "sidepod_blades",
            "front_mudguard_caps",
            "rear_mudguard_caps",
            "front_mudguard_edge_details",
            "rear_mudguard_edge_details",
            "mid_side_generated_panel",
            "rear_side_generated_panels",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("mudguards", 1.28),
            ("side_blade", 1.16),
            ("rear_center_glow", 1.22),
            ("tailwing", 1.16),
            ("center_spine", 0.78),
        ),
    ),
    Candidate(
        "dark_neon_louver",
        "rear_louver_focus",
        "dense rear louver rhythm with restrained spine and alternating guard caps",
        ("rear_louvers", "rear_center_glow", "tail_bar", "tailwing"),
        "#050607",
        "#17191d",
        "#ff149a",
        "#00cfff",
        "#f7fbff",
        0.038,
        0.30,
        0.24,
        22.0,
        "secondary_front",
        (
            "engine_rear_deck",
            "rear_deck_fine_louver_rows",
            "rear_side_generated_panels",
            "rear_floor_generated_panels",
            "tailwing_bands",
            "rear_mudguard_caps",
            "rear_mudguard_edge_details",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("rear_louvers", 1.40),
            ("rear_center_glow", 1.26),
            ("tail_bar", 1.22),
            ("tailwing", 1.18),
            ("side_blade", 0.46),
            ("secondary_blade", 0.55),
            ("nose_spear", 0.70),
        ),
    ),
    Candidate(
        "magenta_cyan_race_proto",
        "race_proto_balance",
        "balanced race prototype layout using nose, spine, side blades, and local aero accents",
        ("nose_spear", "center_spine", "side_wings", "mirrors"),
        "#060506",
        "#1b151d",
        "#ff0090",
        "#00f0ff",
        "#fff8fb",
        0.056,
        0.46,
        0.18,
        17.0,
        "primary_front",
        (
            "center_spine",
            "nose_identity_panel",
            "nose_deck_generated_panels",
            "mid_deck_generated_panels",
            "mid_side_generated_panel",
            "sidepod_blades",
            "side_wings",
            "mirrors_and_holders",
            "licence_plate_blocks",
            "tailwing_bands",
            "underbody_dark",
        ),
        (
            ("nose_spear", 1.22),
            ("center_spine", 1.16),
            ("side_wings", 1.25),
            ("mirrors", 1.28),
            ("rear_louvers", 0.72),
            ("rear_center_glow", 0.82),
        ),
    ),
    Candidate(
        "black_red_cyber_minimal",
        "minimal_red_speedmark",
        "minimal black/red cyber speedmark with narrow cyan counter-lines and low visual noise",
        ("nose_spear", "shoulder_line", "tail_bar", "mudguard_edge"),
        "#040404",
        "#151316",
        "#ff0078",
        "#00d8ff",
        "#f8f3ff",
        0.034,
        0.28,
        0.30,
        12.0,
        "primary_front",
        (
            "nose_identity_panel",
            "center_spine",
            "mid_side_generated_panel",
            "rear_side_generated_panels",
            "tailwing_bands",
            "front_mudguard_edge_details",
            "rear_mudguard_edge_details",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("nose_spear", 1.36),
            ("shoulder_line", 1.32),
            ("tail_bar", 1.18),
            ("mudguard_edge", 1.10),
            ("side_blade", 0.22),
            ("secondary_blade", 0.92),
            ("rear_louvers", 0.20),
        ),
    ),
    Candidate(
        "carbon_gold_circuit",
        "gold_circuit_trace",
        "carbon base with restrained gold highlights and cyan/magenta circuit-trace accents",
        ("center_spine", "side_blade", "mirrors", "rear_louvers"),
        "#050604",
        "#1b1810",
        "#ff2bc6",
        "#00e6ff",
        "#ffd766",
        0.046,
        0.58,
        0.11,
        20.0,
        "secondary_front",
        (
            "center_spine",
            "sidepod_blades",
            "mid_deck_generated_panels",
            "mid_floor_generated_panels",
            "engine_rear_deck",
            "rear_deck_fine_louver_rows",
            "mirrors_and_holders",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("center_spine", 1.02),
            ("side_blade", 1.24),
            ("secondary_blade", 1.18),
            ("rear_louvers", 1.18),
            ("mirrors", 1.42),
            ("tailwing", 0.84),
            ("mudguards", 0.44),
        ),
    ),
    Candidate(
        "teal_magenta_vector",
        "teal_vector_sweep",
        "teal/cyan vector sweep over black with magenta wing and guard punctuation",
        ("side_blade", "center_spine", "side_wings", "mudguards"),
        "#03070a",
        "#0d1b20",
        "#ff00a8",
        "#00ffd5",
        "#eefcff",
        0.052,
        0.62,
        0.09,
        15.0,
        "split",
        (
            "center_spine",
            "sidepod_blades",
            "nose_side_generated_panels",
            "mid_side_generated_panel",
            "side_wings",
            "front_mudguard_caps",
            "rear_mudguard_caps",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("side_blade", 1.38),
            ("center_spine", 1.28),
            ("side_wings", 1.34),
            ("mudguards", 1.18),
            ("nose_spear", 0.72),
            ("rear_center_glow", 0.78),
        ),
    ),
    Candidate(
        "shadow_magenta_split",
        "shadow_split_engine",
        "shadow-heavy split layout with magenta engine deck and cyan rear/underbody structure",
        ("rear_center_glow", "rear_louvers", "underplate", "tailwing"),
        "#020204",
        "#141018",
        "#ff00e0",
        "#00bfff",
        "#fcf1ff",
        0.040,
        0.40,
        0.20,
        24.0,
        "split",
        (
            "engine_rear_deck",
            "rear_deck_fine_louver_rows",
            "rear_side_generated_panels",
            "rear_floor_generated_panels",
            "mid_floor_generated_panels",
            "rear_mudguard_caps",
            "rear_mudguard_edge_details",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("rear_center_glow", 1.42),
            ("rear_louvers", 1.36),
            ("underplate", 1.18),
            ("tailwing", 1.26),
            ("side_blade", 0.58),
            ("secondary_blade", 0.62),
            ("nose_spear", 0.54),
        ),
    ),
    Candidate(
        "white_cyan_nightcore",
        "white_contrast_nightcore",
        "high-contrast white/cyan deck panels over black with magenta identity marks",
        ("center_spine", "nose_spear", "mirrors", "tail_bar"),
        "#050608",
        "#1a1f23",
        "#ff149a",
        "#00eaff",
        "#ffffff",
        0.058,
        0.33,
        0.25,
        19.0,
        "secondary_front",
        (
            "center_spine",
            "nose_identity_panel",
            "nose_deck_generated_panels",
            "mid_deck_generated_panels",
            "rear_floor_generated_panels",
            "mirrors_and_holders",
            "front_mudguard_caps",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("center_spine", 1.26),
            ("nose_spear", 1.20),
            ("mirrors", 1.54),
            ("tail_bar", 1.24),
            ("side_blade", 0.30),
            ("secondary_blade", 0.32),
            ("mudguards", 0.30),
        ),
    ),
    Candidate(
        "monochrome_magenta_pinstripe",
        "mono_pinstripe_cut",
        "near-black minimalist pinstripe using only nose, shoulder, tail, and mirror punctuation",
        ("shoulder_line", "nose_spear", "tail_bar", "mirrors"),
        "#030304",
        "#111114",
        "#ff008c",
        "#00d6ff",
        "#f5f5f7",
        0.026,
        0.22,
        0.34,
        10.0,
        "primary_front",
        (
            "nose_identity_panel",
            "mid_side_generated_panel",
            "rear_side_generated_panels",
            "mirrors_and_holders",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("shoulder_line", 1.48),
            ("nose_spear", 1.22),
            ("tail_bar", 1.28),
            ("mirrors", 1.40),
            ("side_blade", 0.16),
            ("secondary_blade", 0.18),
            ("rear_louvers", 0.14),
            ("mudguards", 0.20),
        ),
    ),
    Candidate(
        "cyan_white_gt_block",
        "heritage_center_block",
        "GT-style white/cyan deck block with black flanks and magenta micro accents",
        ("center_spine", "nose_spear", "mid_deck_generated_panels", "tailwing"),
        "#040506",
        "#12161a",
        "#00dfff",
        "#ff0aa8",
        "#f4f8ff",
        0.075,
        0.24,
        0.28,
        12.0,
        "secondary_front",
        (
            "center_spine",
            "nose_identity_panel",
            "nose_deck_generated_panels",
            "mid_deck_generated_panels",
            "rear_floor_generated_panels",
            "tailwing_bands",
            "side_wings",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("center_spine", 1.50),
            ("nose_spear", 1.28),
            ("mid_deck_generated_panels", 1.16),
            ("tailwing", 1.24),
            ("side_blade", 0.28),
            ("rear_louvers", 0.24),
            ("mudguards", 0.36),
        ),
    ),
    Candidate(
        "neon_checker_tail",
        "checker_tail",
        "black forward body with a checker-pattern tail deck and bright guard punctuation",
        ("rear_louvers", "tailwing", "tail_bar", "mudguard_edge"),
        "#030405",
        "#12151a",
        "#ff00a8",
        "#00eaff",
        "#ffffff",
        0.038,
        0.32,
        0.22,
        26.0,
        "split",
        (
            "engine_rear_deck",
            "rear_deck_fine_louver_rows",
            "rear_side_generated_panels",
            "rear_floor_generated_panels",
            "rear_mudguard_caps",
            "rear_mudguard_edge_details",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("rear_louvers", 1.46),
            ("tailwing", 1.42),
            ("tail_bar", 1.32),
            ("mudguard_edge", 1.24),
            ("center_spine", 0.24),
            ("side_blade", 0.20),
            ("secondary_blade", 0.18),
        ),
    ),
    Candidate(
        "asym_diagonal_sash",
        "diagonal_sash",
        "large diagonal sash across side surfaces with small counter-stripes on deck and tail",
        ("side_blade", "secondary_blade", "shoulder_line", "nose_spear"),
        "#050507",
        "#151821",
        "#ff009d",
        "#00f0ff",
        "#fafcff",
        0.040,
        0.70,
        0.06,
        14.0,
        "primary_front",
        (
            "sidepod_blades",
            "nose_side_generated_panels",
            "mid_side_generated_panel",
            "rear_side_generated_panels",
            "nose_deck_generated_panels",
            "side_wings",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("side_blade", 1.52),
            ("secondary_blade", 1.36),
            ("shoulder_line", 1.20),
            ("nose_spear", 1.10),
            ("rear_louvers", 0.30),
            ("mudguards", 0.42),
        ),
    ),
    Candidate(
        "guard_halo_cyan",
        "guard_halo",
        "mudguard halo design with dark body, cyan guard caps, and magenta edge lighting",
        ("mudguards", "mudguard_edge", "side_wings", "mirrors"),
        "#030507",
        "#0d151c",
        "#ff00b8",
        "#00e5ff",
        "#eaffff",
        0.032,
        0.36,
        0.24,
        16.0,
        "secondary_front",
        (
            "front_mudguard_caps",
            "rear_mudguard_caps",
            "front_mudguard_edge_details",
            "rear_mudguard_edge_details",
            "side_wings",
            "mirrors_and_holders",
            "rear_floor_generated_panels",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("mudguards", 1.48),
            ("mudguard_edge", 1.56),
            ("side_wings", 1.18),
            ("mirrors", 1.24),
            ("center_spine", 0.24),
            ("side_blade", 0.22),
            ("rear_louvers", 0.26),
        ),
    ),
    Candidate(
        "full_panel_cyber_flood",
        "full_panel_dense",
        "dense full-panel cyber layout using side blades, rear louvers, deck panels, and guard edges",
        ("side_blade", "rear_louvers", "center_spine", "mudguard_edge"),
        "#030408",
        "#111827",
        "#ff00c8",
        "#00e0ff",
        "#f8fbff",
        0.068,
        0.55,
        0.12,
        28.0,
        "split",
        (
            "center_spine",
            "sidepod_blades",
            "nose_identity_panel",
            "nose_deck_generated_panels",
            "nose_side_generated_panels",
            "mid_deck_generated_panels",
            "mid_side_generated_panel",
            "mid_floor_generated_panels",
            "engine_rear_deck",
            "rear_deck_fine_louver_rows",
            "rear_side_generated_panels",
            "rear_floor_generated_panels",
            "front_mudguard_caps",
            "rear_mudguard_caps",
            "front_mudguard_edge_details",
            "rear_mudguard_edge_details",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("side_blade", 1.58),
            ("secondary_blade", 1.44),
            ("rear_louvers", 1.62),
            ("center_spine", 1.38),
            ("mudguard_edge", 1.38),
            ("tailwing", 1.28),
            ("rear_center_glow", 1.22),
        ),
    ),
    Candidate(
        "mint_purple_split",
        "split_tone_panels",
        "left/right split-tone panels with mint side flow and purple-magenta deck accents",
        ("center_spine", "side_blade", "mid_side_generated_panel", "tailwing"),
        "#030606",
        "#10201e",
        "#d900ff",
        "#00ffd0",
        "#f7f3ff",
        0.048,
        0.48,
        0.18,
        18.0,
        "split",
        (
            "center_spine",
            "sidepod_blades",
            "mid_side_generated_panel",
            "mid_deck_generated_panels",
            "rear_side_generated_panels",
            "front_mudguard_caps",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("center_spine", 1.18),
            ("side_blade", 1.42),
            ("mid_side_generated_panel", 1.18),
            ("tailwing", 1.12),
            ("mudguard_edge", 0.78),
            ("rear_louvers", 0.58),
        ),
    ),
    Candidate(
        "orange_teal_circuit",
        "carbon_circuit",
        "carbon circuit-board layout with orange highlight traces plus teal and magenta anchors",
        ("shoulder_line", "rear_louvers", "mirrors", "tail_bar"),
        "#040503",
        "#171911",
        "#ff00a0",
        "#00e8d8",
        "#ff9d2e",
        0.042,
        0.44,
        0.16,
        24.0,
        "primary_front",
        (
            "center_spine",
            "mid_deck_generated_panels",
            "mid_floor_generated_panels",
            "rear_deck_fine_louver_rows",
            "rear_floor_generated_panels",
            "mirrors_and_holders",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("shoulder_line", 1.44),
            ("rear_louvers", 1.36),
            ("mirrors", 1.34),
            ("tail_bar", 1.22),
            ("center_spine", 0.82),
            ("side_blade", 0.42),
            ("mudguards", 0.34),
        ),
    ),
    Candidate(
        "white_magenta_rally_blocks",
        "white_race_blocks",
        "high-contrast rally block composition with white deck slabs and magenta/cyan edges",
        ("nose_spear", "center_spine", "tail_bar", "mirrors"),
        "#060607",
        "#202126",
        "#ff008d",
        "#00dfff",
        "#ffffff",
        0.072,
        0.26,
        0.30,
        12.0,
        "secondary_front",
        (
            "center_spine",
            "nose_identity_panel",
            "nose_deck_generated_panels",
            "mid_deck_generated_panels",
            "rear_floor_generated_panels",
            "side_wings",
            "tailwing_bands",
            "front_mudguard_caps",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("nose_spear", 1.34),
            ("center_spine", 1.46),
            ("tailwing", 0.48),
            ("side_wings", 0.48),
            ("tail_bar", 1.18),
            ("mirrors", 1.20),
            ("side_blade", 0.34),
            ("rear_louvers", 0.32),
            ("mudguard_edge", 0.32),
        ),
    ),
    Candidate(
        "crimson_cyan_arrow",
        "arrowhead_proto",
        "front arrowhead prototype with broad cyan shoulders and crimson-magenta rear echoes",
        ("nose_spear", "side_blade", "shoulder_line", "rear_center_glow"),
        "#040405",
        "#18151a",
        "#ff008c",
        "#00d8ff",
        "#fff4f8",
        0.060,
        0.38,
        0.20,
        16.0,
        "primary_front",
        (
            "center_spine",
            "nose_identity_panel",
            "nose_side_generated_panels",
            "nose_floor_generated_panels",
            "sidepod_blades",
            "mid_floor_generated_panels",
            "rear_side_generated_panels",
            "tailwing_bands",
            *DEFAULT_PANEL_CATALOG_TARGETS,
        ),
        (
            ("nose_spear", 1.48),
            ("side_blade", 1.22),
            ("shoulder_line", 1.30),
            ("rear_center_glow", 1.24),
            ("secondary_blade", 0.88),
            ("rear_louvers", 0.72),
            ("mudguards", 0.48),
        ),
    ),
]


LANE_GRAPHIC_ARCHETYPES = {
    "side_blade_sweep": "wide_side_blade",
    "center_spine_focus": "center_spine",
    "split_guard_flow": "split_tone_panels",
    "rear_louver_focus": "rear_louver_stack",
    "race_proto_balance": "arrowhead_proto",
    "minimal_red_speedmark": "minimal_pinstripe",
    "gold_circuit_trace": "carbon_circuit",
    "teal_vector_sweep": "vector_wedge",
    "shadow_split_engine": "rear_louver_stack",
    "white_contrast_nightcore": "white_race_blocks",
    "mono_pinstripe_cut": "minimal_pinstripe",
    "heritage_center_block": "heritage_center_block",
    "checker_tail": "checker_tail",
    "diagonal_sash": "diagonal_sash",
    "guard_halo": "guard_halo",
    "full_panel_dense": "full_panel_dense",
    "split_tone_panels": "split_tone_panels",
    "carbon_circuit": "carbon_circuit",
    "white_race_blocks": "white_race_blocks",
    "arrowhead_proto": "arrowhead_proto",
}
LANE_BASE_MASK_STRENGTHS = {
    "minimal_red_speedmark": 0.06,
    "mono_pinstripe_cut": 0.04,
    "heritage_center_block": 0.10,
    "checker_tail": 0.10,
    "guard_halo": 0.08,
    "full_panel_dense": 0.20,
    "white_race_blocks": 0.10,
}


def _candidate_catalog_targets(candidate: Candidate) -> list[str]:
    return list(dict.fromkeys(candidate.panel_catalog_targets))


def _candidate_mask_strengths(candidate: Candidate) -> dict[str, float]:
    strengths = {name: candidate.base_mask_strength for name in PREMIUM_MASK_NAMES}
    strengths.update({name: float(value) for name, value in candidate.mask_strengths})
    return strengths


def _candidate_panel_family_strengths(candidate: Candidate) -> dict[str, float]:
    targets = set(_candidate_catalog_targets(candidate))
    strengths: dict[str, float] = {}
    for name in PANEL_FAMILY_MASK_NAMES:
        if name in targets:
            strengths[name] = 1.0
    return strengths


def _blend_strength(strengths: dict[str, float], name: str, base: float) -> float:
    return base * strengths.get(name, 1.0)


def _panel_family_color(candidate: Candidate, name: str) -> str:
    if "floor" in name:
        return candidate.base2
    if "side" in name or "louver" in name:
        return candidate.secondary
    return candidate.primary


def _axis_fields(fields: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    pos = fields["pos"]
    axes = fields["axes"]
    length = pos[..., axes["LEN"]]
    lateral = pos[..., axes["LAT"]]
    height = pos[..., axes["HGT"]]
    symmetry = np.abs(lateral - 0.5)
    return length, lateral, height, symmetry


def _soft(mask: np.ndarray, sigma: float = 1.2) -> np.ndarray:
    return np.clip(gaussian_filter(mask.astype(np.float32), sigma=sigma), 0.0, 1.0)


def _blend(rgb: np.ndarray, mask: np.ndarray, color: str, strength: float = 1.0) -> None:
    amount = np.clip(_soft(mask) * strength, 0.0, 1.0)
    if amount.max() <= 0:
        return
    rgb[:] = rgb * (1.0 - amount[..., None]) + hx(color) * amount[..., None]


def _line_mask(field: np.ndarray, center: float | np.ndarray, width: float) -> np.ndarray:
    return np.abs(field - center) <= width


def _phase_mask(
    mask: np.ndarray,
    length: np.ndarray,
    symmetry: np.ndarray,
    *,
    length_steps: float,
    side_steps: float,
    duty: float,
) -> np.ndarray:
    phase = (np.floor(length * length_steps) + np.floor(symmetry * side_steps)).astype(np.int32)
    return mask & ((phase % 2) == 0) & (((length * length_steps + symmetry * side_steps) % 1.0) < duty)


def _panel_union(masks: dict[str, np.ndarray], names: tuple[str, ...]) -> np.ndarray:
    union = np.zeros_like(next(iter(masks.values())), dtype=bool)
    for name in names:
        union |= masks[name]
    return union


def _apply_graphic_archetype(
    rgb: np.ndarray,
    masks: dict[str, np.ndarray],
    fields: dict[str, Any],
    candidate: Candidate,
) -> np.ndarray:
    coverage = fields["coverage"]
    labels = fields["labels"]
    length, lateral, height, symmetry = _axis_fields(fields)
    body = coverage & (labels > 0)
    upper = body & (height > 0.46)
    lower = body & (height <= 0.46)
    rear = body & (length < 0.36)
    nose = body & (length > 0.70)
    extra_accent = np.zeros_like(coverage, dtype=bool)
    archetype = candidate.graphic_archetype

    if archetype == "minimal_pinstripe":
        pin = (
            masks["shoulder_line"]
            | (masks["nose_spear"] & (length > 0.78))
            | (masks["tail_bar"] & (height > 0.32))
        )
        counter = masks["mirrors"] | (masks["mudguard_edge"] & ((length > 0.78) | (length < 0.18)))
        highlight_mark = masks["side_wings"] | (masks["tailwing"] & (length < 0.16))
        _blend(rgb, pin, candidate.primary, 1.22)
        _blend(rgb, counter, candidate.secondary, 0.88)
        _blend(rgb, highlight_mark, candidate.highlight, 0.58)
        extra_accent |= pin | counter | highlight_mark
    elif archetype == "heritage_center_block":
        deck_block = _panel_union(
            masks,
            ("nose_deck_generated_panels", "mid_deck_generated_panels", "center_spine"),
        ) & upper
        side_cut = masks["side_wings"] | (masks["tailwing"] & (symmetry > 0.18))
        _blend(rgb, deck_block, candidate.highlight, 0.58)
        _blend(rgb, deck_block & _line_mask(symmetry, 0.0, 0.070), candidate.secondary, 0.62)
        _blend(rgb, side_cut, candidate.primary, 0.74)
        extra_accent |= (deck_block & _line_mask(symmetry, 0.0, 0.070)) | side_cut
    elif archetype == "checker_tail":
        tail_zone = _panel_union(
            masks,
            ("tailwing", "rear_louvers", "rear_deck_fine_louver_rows", "rear_floor_generated_panels"),
        ) & rear
        checker = _phase_mask(tail_zone, length, symmetry, length_steps=34.0, side_steps=42.0, duty=0.72)
        _blend(rgb, checker, candidate.highlight, 0.94)
        _blend(rgb, tail_zone & ~checker, candidate.primary, 0.58)
        _blend(rgb, masks["mudguard_edge"] & rear, candidate.secondary, 0.88)
        extra_accent |= tail_zone | (masks["mudguard_edge"] & rear)
    elif archetype == "diagonal_sash":
        center = np.clip(0.09 + 0.48 * (1.0 - length), 0.10, 0.42)
        sash = body & (height > 0.22) & (height < 0.70) & _line_mask(symmetry, center, 0.048)
        counter = body & (height > 0.30) & _line_mask(symmetry, np.clip(center + 0.075, 0.14, 0.48), 0.018)
        _blend(rgb, sash, candidate.secondary, 0.98)
        _blend(rgb, counter, candidate.primary, 0.86)
        _blend(rgb, masks["nose_spear"] & nose, candidate.primary, 0.82)
        extra_accent |= sash | counter | (masks["nose_spear"] & nose)
    elif archetype == "guard_halo":
        caps = masks["mudguards"]
        edge = masks["mudguard_edge"]
        _blend(rgb, caps, candidate.secondary, 1.00)
        _blend(rgb, edge, candidate.primary, 1.18)
        _blend(rgb, masks["side_wings"] | masks["mirrors"], candidate.highlight, 0.76)
        cap_highlight = caps & ((height > 0.58) | (symmetry > 0.36))
        spine_marker = masks["center_spine"] | (masks["tailwing"] & (symmetry > 0.16))
        _blend(rgb, cap_highlight, candidate.highlight, 0.50)
        _blend(rgb, spine_marker, candidate.highlight, 0.70)
        extra_accent |= caps | edge | masks["side_wings"] | masks["mirrors"] | cap_highlight | spine_marker
    elif archetype == "full_panel_dense":
        panel_field = _panel_union(
            masks,
            (
                "nose_deck_generated_panels",
                "nose_side_generated_panels",
                "mid_deck_generated_panels",
                "mid_side_generated_panel",
                "rear_side_generated_panels",
                "rear_deck_fine_louver_rows",
            ),
        )
        bright = masks["center_spine"] | masks["side_blade"] | masks["rear_louvers"] | masks["mudguard_edge"]
        _blend(rgb, panel_field & upper, candidate.primary, 0.36)
        _blend(rgb, panel_field & lower, candidate.secondary, 0.34)
        _blend(rgb, bright, candidate.secondary, 0.92)
        _blend(rgb, masks["secondary_blade"] | masks["rear_center_glow"], candidate.primary, 0.84)
        extra_accent |= bright | masks["secondary_blade"] | masks["rear_center_glow"]
    elif archetype == "split_tone_panels":
        panel_field = _panel_union(
            masks,
            ("mid_side_generated_panel", "mid_deck_generated_panels", "rear_side_generated_panels", "side_blade"),
        )
        left = panel_field & (lateral < 0.5)
        right = panel_field & (lateral >= 0.5)
        _blend(rgb, left, candidate.primary, 0.58)
        _blend(rgb, right, candidate.secondary, 0.58)
        _blend(rgb, masks["center_spine"], candidate.highlight, 0.56)
        extra_accent |= masks["side_blade"] | masks["center_spine"]
    elif archetype == "carbon_circuit":
        deck = upper & (length > 0.22) & (length < 0.74)
        traces = deck & (
            _line_mask(symmetry, 0.18, 0.012)
            | _line_mask(symmetry, 0.31, 0.010)
            | (((np.floor(length * 18.0) % 4) == 0) & (symmetry > 0.08) & (symmetry < 0.36))
        )
        _blend(rgb, traces, candidate.highlight, 0.92)
        _blend(rgb, masks["rear_louvers"], candidate.secondary, 0.72)
        _blend(rgb, masks["tail_bar"] | masks["mirrors"], candidate.primary, 0.70)
        extra_accent |= traces | masks["rear_louvers"] | masks["tail_bar"] | masks["mirrors"]
    elif archetype == "white_race_blocks":
        slabs = _panel_union(masks, ("nose_deck_generated_panels", "mid_deck_generated_panels", "center_spine")) & upper
        lower_blocks = _panel_union(masks, ("rear_floor_generated_panels", "side_wings", "tailwing"))
        _blend(rgb, slabs, candidate.highlight, 0.72)
        _blend(rgb, slabs & _line_mask(symmetry, 0.0, 0.065), candidate.secondary, 0.54)
        _blend(rgb, lower_blocks, candidate.primary, 0.56)
        extra_accent |= slabs & _line_mask(symmetry, 0.0, 0.065)
    elif archetype == "arrowhead_proto":
        arrow_center = np.clip(0.040 + 0.28 * (1.0 - length), 0.05, 0.30)
        arrow = nose & _line_mask(symmetry, arrow_center, 0.070)
        shoulders = lower & (length > 0.45) & (length < 0.76) & _line_mask(symmetry, 0.31, 0.045)
        _blend(rgb, arrow, candidate.primary, 1.15)
        _blend(rgb, shoulders, candidate.secondary, 0.84)
        _blend(rgb, shoulders & (length > 0.56), candidate.highlight, 0.42)
        _blend(rgb, masks["rear_center_glow"], candidate.primary, 0.82)
        extra_accent |= arrow | shoulders | masks["rear_center_glow"]
    elif archetype == "vector_wedge":
        wedge = lower & (length > 0.30) & (length < 0.82) & (symmetry > 0.14) & (
            symmetry < np.clip(0.21 + 0.34 * (length - 0.30), 0.21, 0.42)
        )
        _blend(rgb, wedge, candidate.secondary, 0.58)
        _blend(rgb, masks["side_blade"] | masks["side_wings"], candidate.primary, 0.70)
        extra_accent |= wedge | masks["side_blade"] | masks["side_wings"]
    elif archetype == "rear_louver_stack":
        stack = masks["rear_louvers"] | masks["rear_deck_fine_louver_rows"] | masks["rear_center_glow"]
        counter = masks["tailwing"] | masks["mudguard_edge"] | masks["secondary_blade"]
        _blend(rgb, stack, candidate.primary, 0.80)
        _blend(rgb, counter, candidate.secondary, 0.70)
        extra_accent |= stack | counter
    elif archetype == "wide_side_blade":
        blade_field = masks["side_blade"] | masks["secondary_blade"] | masks["nose_side_generated_panels"]
        _blend(rgb, blade_field, candidate.secondary, 0.58)
        _blend(rgb, masks["nose_spear"], candidate.primary, 0.76)
        extra_accent |= blade_field | masks["nose_spear"]
    elif archetype == "center_spine":
        spine = masks["center_spine"] | masks["nose_spear"]
        _blend(rgb, spine, candidate.secondary, 0.72)
        _blend(rgb, masks["tailwing"] | masks["mudguard_edge"], candidate.primary, 0.56)
        extra_accent |= spine | masks["tailwing"] | masks["mudguard_edge"]
    else:
        balanced = masks["center_spine"] | masks["side_blade"] | masks["tailwing"]
        _blend(rgb, balanced, candidate.primary, 0.46)
        extra_accent |= balanced

    return extra_accent


def _mask_params(candidate: Candidate) -> PremiumMaskParams:
    return PremiumMaskParams(
        spine_width=candidate.spine_width,
        blade_slope=candidate.blade_slope,
        blade_offset=candidate.blade_offset,
        rear_louver_count=candidate.rear_louver_count,
    )


def _build_masks(fields: dict[str, Any], candidate: Candidate) -> dict[str, np.ndarray]:
    panel_masks = build_stock_panel_masks(fields, _mask_params(candidate))
    return {name: panel.mask for name, panel in panel_masks.items()}


def build_premium_rgba(candidate: Candidate) -> tuple[Image.Image, dict[str, float], dict[str, dict[str, float | int]]]:
    fields = load_fields()
    coverage = fields["coverage"]
    labels = fields["labels"]
    length, _lateral, height, symmetry = _axis_fields(fields)
    masks = _build_masks(fields, candidate)
    strengths = _candidate_mask_strengths(candidate)
    panel_family_strengths = _candidate_panel_family_strengths(candidate)

    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    alpha = np.full((SIZE, SIZE), 112, dtype=np.float32)

    depth = 0.62 + 0.18 * length + 0.12 * height - 0.10 * np.clip(symmetry / 0.5, 0, 1)
    rgb[coverage] = hx(candidate.base)
    rgb[coverage] = rgb[coverage] * (1.0 - depth[coverage, None]) + hx(candidate.base2) * depth[coverage, None]

    _blend(rgb, masks["center_spine"], candidate.primary, _blend_strength(strengths, "center_spine", 0.95))
    _blend(rgb, masks["nose_spear"], candidate.primary, _blend_strength(strengths, "nose_spear", 1.00))
    _blend(rgb, masks["side_blade"], candidate.secondary, _blend_strength(strengths, "side_blade", 0.92))
    _blend(rgb, masks["secondary_blade"], candidate.primary, _blend_strength(strengths, "secondary_blade", 0.72))
    _blend(rgb, masks["rear_louvers"], candidate.secondary, _blend_strength(strengths, "rear_louvers", 0.86))
    _blend(rgb, masks["rear_center_glow"], candidate.primary, _blend_strength(strengths, "rear_center_glow", 0.82))
    _blend(rgb, masks["shoulder_line"], candidate.highlight, _blend_strength(strengths, "shoulder_line", 0.62))
    _blend(rgb, masks["tail_bar"], candidate.secondary, _blend_strength(strengths, "tail_bar", 0.95))

    underbody = masks["main_body_under"] | masks["underplate"]
    underbody_strength = max(strengths["main_body_under"], strengths["underplate"])
    _blend(rgb, underbody, "#020204", 0.42 * underbody_strength)
    _blend(rgb, masks["tailwing"], candidate.primary, _blend_strength(strengths, "tailwing", 0.34))
    _blend(rgb, masks["tailwing"] & (height > 0.52), candidate.secondary, _blend_strength(strengths, "tailwing", 0.28))
    _blend(rgb, masks["side_wings"], candidate.secondary, _blend_strength(strengths, "side_wings", 0.46))
    _blend(rgb, masks["mirrors"], candidate.highlight, _blend_strength(strengths, "mirrors", 0.54))

    panel_family_accent = np.zeros_like(coverage, dtype=bool)
    for mask_name, strength in panel_family_strengths.items():
        panel_family_accent |= masks[mask_name]
        _blend(rgb, masks[mask_name], _panel_family_color(candidate, mask_name), 0.18 * strength)

    archetype_accent = _apply_graphic_archetype(rgb, masks, fields, candidate)

    if candidate.mudguard_mode == "split":
        _blend(rgb, masks["mudguards"] & (length > 0.5), candidate.primary, _blend_strength(strengths, "mudguards", 0.72))
        _blend(rgb, masks["mudguards"] & (length <= 0.5), candidate.secondary, _blend_strength(strengths, "mudguards", 0.72))
    elif candidate.mudguard_mode == "secondary_front":
        _blend(rgb, masks["mudguards"], candidate.primary, _blend_strength(strengths, "mudguards", 0.38))
        _blend(rgb, masks["mudguard_edge"] & (length > 0.5), candidate.secondary, _blend_strength(strengths, "mudguard_edge", 0.88))
        _blend(rgb, masks["mudguard_edge"] & (length <= 0.5), candidate.primary, _blend_strength(strengths, "mudguard_edge", 0.78))
    else:
        _blend(rgb, masks["mudguards"], candidate.secondary, _blend_strength(strengths, "mudguards", 0.38))
        _blend(rgb, masks["mudguard_edge"] & (length > 0.5), candidate.primary, _blend_strength(strengths, "mudguard_edge", 0.88))
        _blend(rgb, masks["mudguard_edge"] & (length <= 0.5), candidate.secondary, _blend_strength(strengths, "mudguard_edge", 0.78))

    seams = binary_dilation(
        ((labels != np.roll(labels, 1, 0)) | (labels != np.roll(labels, 1, 1))) & (labels > 0),
        iterations=1,
    )
    rgb[seams] *= 0.72

    ao_path = REF_DIR / "official_prelight_AO.png"
    if ao_path.exists():
        ao = np.asarray(Image.open(ao_path).convert("L").resize((SIZE, SIZE)), dtype=np.float32)
        rgb *= (0.76 + 0.24 * ao / 255.0)[..., None]

    active_accent = np.zeros_like(coverage, dtype=bool)
    for mask_name, strength in strengths.items():
        if strength >= 0.35 and mask_name not in {"main_body_under", "underplate"}:
            active_accent |= masks[mask_name]
    for mask_name in candidate.distinctive_masks:
        active_accent |= masks[mask_name]
    accent = active_accent | archetype_accent
    alpha[accent] = 148
    alpha[panel_family_accent & ~accent] = np.maximum(alpha[panel_family_accent & ~accent], 124)
    alpha[masks["shoulder_line"]] = 136
    alpha[underbody] = 118
    for mask_name in candidate.distinctive_masks:
        subtle_distinctive = masks[mask_name] & ~accent
        alpha[subtle_distinctive] = np.maximum(alpha[subtle_distinctive], 128)

    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    metrics = _style_metrics(out, coverage)
    mask_metrics = _mask_style_metrics(out, masks, PREMIUM_MASK_NAMES)
    return Image.fromarray(out, "RGBA"), metrics, mask_metrics


def _style_metrics(rgba: np.ndarray, coverage: np.ndarray) -> dict[str, float]:
    rgb = rgba[..., :3].astype(np.float32)
    lum = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    denom = max(int(coverage.sum()), 1)
    magenta = coverage & (rgb[..., 0] > 135) & (rgb[..., 2] > 105) & (rgb[..., 1] < 95)
    cyan = coverage & (rgb[..., 1] > 110) & (rgb[..., 2] > 130) & (rgb[..., 0] < 95)
    dark = coverage & (lum < 80)
    return {
        "dark_pixel_ratio": round(float(dark.sum() / denom), 6),
        "magenta_accent_ratio": round(float(magenta.sum() / denom), 6),
        "cyan_accent_ratio": round(float(cyan.sum() / denom), 6),
    }


def _mask_style_metrics(
    rgba: np.ndarray,
    masks: dict[str, np.ndarray],
    names: list[str],
) -> dict[str, dict[str, float | int]]:
    rgb = rgba[..., :3].astype(np.float32)
    alpha = rgba[..., 3].astype(np.float32)
    lum = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    metrics: dict[str, dict[str, float | int]] = {}
    for name in names:
        mask = masks[name]
        pixel_count = int(mask.sum())
        if pixel_count == 0:
            metrics[name] = {
                "pixel_count": 0,
                "mean_alpha": 0.0,
                "mean_luminance": 0.0,
                "mean_chroma": 0.0,
                "high_alpha_pixel_ratio": 0.0,
            }
            continue
        mask_alpha = alpha[mask]
        metrics[name] = {
            "pixel_count": pixel_count,
            "mean_alpha": round(float(mask_alpha.mean()), 6),
            "mean_luminance": round(float(lum[mask].mean()), 6),
            "mean_chroma": round(float(chroma[mask].mean()), 6),
            "high_alpha_pixel_ratio": round(float((mask_alpha >= 136).sum() / pixel_count), 6),
        }
    return metrics


def _alpha_metrics(rgba: np.ndarray, coverage: np.ndarray) -> dict[str, float | int | list[int]]:
    alpha = rgba[..., 3][coverage].astype(np.uint8)
    if alpha.size == 0:
        return {
            "min_alpha": 0,
            "max_alpha": 0,
            "mean_alpha": 0.0,
            "unique_alpha_values": [],
            "high_alpha_pixel_ratio": 0.0,
        }
    return {
        "min_alpha": int(alpha.min()),
        "max_alpha": int(alpha.max()),
        "mean_alpha": round(float(alpha.mean()), 6),
        "unique_alpha_values": [int(value) for value in np.unique(alpha)],
        "high_alpha_pixel_ratio": round(float((alpha >= 136).sum() / alpha.size), 6),
    }


def _load_reference_guidance() -> dict[str, Any] | None:
    if not DEFAULT_REFERENCE_INDEX.exists():
        return None
    write_reference_style_guidance(DEFAULT_REFERENCE_INDEX, DEFAULT_GUIDANCE)
    return build_reference_style_guidance(DEFAULT_REFERENCE_INDEX)


def _write_candidate(candidate: Candidate, reference_guidance: dict[str, Any] | None = None) -> dict[str, str]:
    out_skin = ROOT / "out" / "skins" / f"{candidate.name}.zip"
    out_preview = ROOT / "out" / "previews" / f"{candidate.name}_projected_side_top_rear.png"
    out_atlas = ROOT / "out" / "previews" / f"{candidate.name}_atlas.png"
    out_report = ROOT / "out" / "reports" / f"{candidate.name}.json"
    for path in (out_skin.parent, out_preview.parent, out_report.parent):
        path.mkdir(parents=True, exist_ok=True)

    image, metrics, mask_style_metrics = build_premium_rgba(candidate)
    fields = load_fields()
    alpha_metrics = _alpha_metrics(np.asarray(image), fields["coverage"])
    icon = image.convert("RGB").resize((64, 64), Image.Resampling.LANCZOS).convert("RGBA")

    with zipfile.ZipFile(out_skin, "w", zipfile.ZIP_DEFLATED) as zf:
        write_stable_zip_entry(zf, "Diffuse.dds", build_dds_dxt5_bytes(image, mipmaps=True))
        write_stable_zip_entry(zf, "Icon.dds", build_dds_dxt5_bytes(icon, mipmaps=True))

    image.save(out_atlas)
    rgba = np.asarray(image)
    side = project_view(rgba, "side", fields)
    top = project_view(rgba, "top", fields)
    rear = project_view(rgba, "rear", fields)
    pad = 14
    canvas = Image.new("RGB", (side.width + rear.width + pad * 3, side.height + top.height + pad * 3), (10, 10, 12))
    canvas.paste(side, (pad, pad))
    canvas.paste(top, (pad, pad * 2 + side.height))
    canvas.paste(rear, (pad * 2 + side.width, pad))
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 2), "side", fill=(230, 230, 240))
    draw.text((pad, pad + side.height + 2), "top", fill=(230, 230, 240))
    draw.text((pad * 2 + side.width, 2), "rear", fill=(230, 230, 240))
    canvas.save(out_preview)
    mask_strengths = _candidate_mask_strengths(candidate)
    panel_family_strengths = _candidate_panel_family_strengths(candidate)

    report = {
        "skin_name": candidate.name,
        "route": "stock_diffuse_only",
        "package_files": ["Diffuse.dds", "Icon.dds"],
        "tmuf_smoke_test": "not_run",
        "proof_gate": {
            "calibration_stock_diffuse": "required_before_proven_use",
            "premium_visual_acceptance": "required_after_generation",
        },
        "evidence_status": {
            "stock_diffuse_route": "proven_by_local_docs_and_package_contract",
            "gbuffer_mapping": "experimental_until_tmuf_smoke",
            "psd_parts_masks": "local_authoritative_input",
            "ao_prelight": "local_authoritative_input",
            "donor_gbx": "not_used",
            "details_dds": "not_used",
            "projshad_dds": "not_used",
        },
        "input_evidence": input_evidence(PREMIUM_DIFFUSE_INPUTS),
        "output_artifacts": stock_output_artifacts(out_skin, out_atlas, out_preview),
        "design_lane": {
            "lane_id": candidate.lane_id,
            "graphic_archetype": candidate.graphic_archetype,
            "composition_focus": candidate.composition_focus,
            "distinctive_masks": list(candidate.distinctive_masks),
            "primary_catalog_targets": _candidate_catalog_targets(candidate),
            "catalog_target_count": len(_candidate_catalog_targets(candidate)),
            "evidence_status": "recipe_metadata_not_tmuf_proof",
            "parameter_signature": {
                "spine_width": candidate.spine_width,
                "blade_slope": candidate.blade_slope,
                "blade_offset": candidate.blade_offset,
                "rear_louver_count": candidate.rear_louver_count,
                "mudguard_mode": candidate.mudguard_mode,
                "base_mask_strength": candidate.base_mask_strength,
            },
        },
        "render_profile": {
            "lane_specific_strengths": True,
            "graphic_archetype": candidate.graphic_archetype,
            "evidence_status": "recipe_metadata_not_tmuf_proof",
            "mask_strengths": mask_strengths,
            "panel_family_strengths": panel_family_strengths,
            "distinctive_mask_strengths": {
                name: mask_strengths[name] for name in candidate.distinctive_masks
            },
            "damped_masks": [
                name for name, strength in mask_strengths.items() if strength < 1.0
            ],
        },
        "alpha_policy": {
            "route": "conservative_dxt5_alpha",
            "material_effect_status": "not_proven_until_tmuf_smoke",
            "tmuf_gloss_claim": "none",
            "base_alpha": 112,
            "underbody_alpha": 118,
            "shoulder_alpha": 136,
            "accent_alpha": 148,
        },
        "alpha_metrics": alpha_metrics,
        "design_rules": [
            "black_charcoal_base",
            "magenta_cyan_accents",
            "broad_gbuffer_aligned_shapes",
            "symmetric_rear_engine_panels",
            "proven_local_panel_accents",
            "no_vignette",
            "no_random_scatter",
            "no_stadiumcar_v2_uvs",
            "no_ch2026_donor_assumptions",
        ],
        "panel_catalog_targets": _candidate_catalog_targets(candidate),
        "panel_visual_coverage": build_panel_visual_coverage(
            _candidate_catalog_targets(candidate),
            mask_style_metrics,
        ),
        "masks_used": PREMIUM_MASK_NAMES,
        "mask_evidence": mask_report_entries(
            build_stock_panel_masks(load_fields(), _mask_params(candidate)),
            PREMIUM_MASK_NAMES,
        ),
        "mask_style_metrics": mask_style_metrics,
        "style_metrics": metrics,
        "known_risks": [
            "GBuffer placement remains experimental until the calibration skin is smoke-tested in TMUF.",
            "Projected previews are local proof aids; they are not a substitute for in-game visual acceptance.",
            "Diffuse alpha is conservative and not a fully tuned gloss/specular map yet.",
        ],
    }
    if reference_guidance is not None:
        report["reference_style_guidance"] = guidance_report_block(reference_guidance, DEFAULT_GUIDANCE)
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")

    return {
        "name": candidate.name,
        "zip": str(out_skin),
        "atlas": str(out_atlas),
        "projection": str(out_preview),
        "report": str(out_report),
    }


def _batch_candidate_entry(report: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "skin_name": report["skin_name"],
        "route": report["route"],
        "package_files": report["package_files"],
        "tmuf_smoke_test": report["tmuf_smoke_test"],
        "gbuffer_mapping": report["evidence_status"]["gbuffer_mapping"],
        "design_lane": report["design_lane"],
        "render_profile": report["render_profile"],
        "style_metrics": report["style_metrics"],
        "alpha_metrics": report["alpha_metrics"],
        "panel_catalog_targets": report["panel_catalog_targets"],
        "output_artifacts": report["output_artifacts"],
    }
    if "reference_style_guidance" in report:
        entry["reference_style_guidance"] = report["reference_style_guidance"]
    return entry


def write_visual_review_board(reports: list[dict[str, Any]], path: Path = REVIEW_BOARD) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    row_h = 278
    header_h = 70
    width = 1260
    height = header_h + row_h * max(len(reports), 1) + 24
    canvas = Image.new("RGB", (width, height), (9, 10, 12))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), "Premium Stock Diffuse Candidate Review Board", fill=(238, 240, 245))
    draw.text(
        (24, 42),
        "Local visual comparison only; does not prove TMUF smoke, GBuffer mapping, or in-game acceptance.",
        fill=(170, 176, 186),
    )

    for row, report in enumerate(reports):
        y = header_h + row * row_h
        lane = report["design_lane"]
        metrics = report["style_metrics"]
        alpha = report["alpha_metrics"]
        atlas_path = ROOT / report["output_artifacts"]["atlas_preview"]["path"]
        projection_path = ROOT / report["output_artifacts"]["projected_preview"]["path"]

        draw.rectangle((16, y + 8, width - 16, y + row_h - 10), outline=(58, 64, 76), width=1)
        draw.text((32, y + 22), report["skin_name"], fill=(240, 242, 247))
        draw.text((32, y + 46), lane["lane_id"], fill=(93, 210, 255))
        draw.text((32, y + 70), _shorten(lane["composition_focus"], 58), fill=(188, 194, 204))
        draw.text(
            (32, y + 104),
            (
                f"dark={metrics['dark_pixel_ratio']:.3f}  "
                f"magenta={metrics['magenta_accent_ratio']:.3f}  "
                f"cyan={metrics['cyan_accent_ratio']:.3f}  "
                f"alpha_mean={alpha['mean_alpha']:.1f}"
            ),
            fill=(214, 218, 225),
        )
        draw.text(
            (32, y + 132),
            _shorten("targets=" + ", ".join(lane["primary_catalog_targets"][:5]), 64),
            fill=(150, 156, 168),
        )
        draw.text((32, y + 158), "proof: TMUF smoke pending", fill=(255, 190, 92))

        projection = Image.open(projection_path).convert("RGB")
        projection.thumbnail((520, 214), Image.Resampling.LANCZOS)
        projection_frame = Image.new("RGB", (540, 224), (16, 17, 20))
        projection_frame.paste(projection, ((540 - projection.width) // 2, (224 - projection.height) // 2))
        canvas.paste(projection_frame, (440, y + 28))

        atlas = Image.open(atlas_path).convert("RGB")
        atlas.thumbnail((190, 190), Image.Resampling.LANCZOS)
        atlas_frame = Image.new("RGB", (210, 210), (16, 17, 20))
        atlas_frame.paste(atlas, ((210 - atlas.width) // 2, (210 - atlas.height) // 2))
        canvas.paste(atlas_frame, (1014, y + 35))

    canvas.save(path)
    return path


def _shorten(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 1)] + "..."


def write_batch_index(outputs: list[dict[str, str]], reference_guidance: dict[str, Any] | None = None) -> Path:
    reports = [json.loads(Path(item["report"]).read_text()) for item in outputs]
    review_board = write_visual_review_board(reports)
    index = {
        "schema": "tmuf_premium_skin_lab.premium_batch_index.v1",
        "route": "stock_diffuse_only",
        "candidate_count": len(reports),
        "does_not_prove_tmuf_smoke": True,
        "tmuf_smoke_status": "pending",
        "gbuffer_mapping": "experimental_until_tmuf_smoke",
        "completion_status": "not_complete_tmuf_smoke_pending",
        "required_before_promotion": [
            "run_tmuf_calibration_smoke_test",
            "record_tmuf_smoke_evidence",
            "evaluate_then_apply_tmuf_smoke_gate",
        ],
        "visual_review_board": artifact_entry(review_board),
        "visual_review_board_policy": {
            "does_not_prove_tmuf_smoke": True,
            "review_scope": "local_candidate_comparison_only",
            "requires_manual_visual_acceptance": True,
        },
        "candidates": [_batch_candidate_entry(report) for report in reports],
    }
    if reference_guidance is not None:
        index["reference_style_guidance"] = guidance_report_block(reference_guidance, DEFAULT_GUIDANCE)
    BATCH_INDEX.parent.mkdir(parents=True, exist_ok=True)
    BATCH_INDEX.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    return BATCH_INDEX


def save_batch() -> list[dict[str, str]]:
    reference_guidance = _load_reference_guidance()
    outputs = [_write_candidate(candidate, reference_guidance) for candidate in CANDIDATES]
    write_batch_index(outputs, reference_guidance)
    return outputs


def main() -> int:
    outputs = save_batch()
    for item in outputs:
        print(f"wrote {item['zip']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
