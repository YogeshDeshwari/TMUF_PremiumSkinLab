from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np


PSD_PARTS_JSON = "resources/authoritative/parts/psd_parts.json"
PSD_PARTS_LABELS = "resources/authoritative/parts/psd_parts_labels.npy"
GBUFFER_POSITION = "resources/authoritative/gbuffer/position_2048.npy"
GBUFFER_COVERAGE = "resources/authoritative/gbuffer/coverage_2048.npy"
GBUFFER_EXTENTS = "resources/authoritative/gbuffer/extents_2048.json"


@dataclass(frozen=True)
class PremiumMaskParams:
    spine_width: float = 0.050
    blade_slope: float = 0.42
    blade_offset: float = 0.16
    rear_louver_count: float = 16.0


@dataclass(frozen=True)
class StockPanelMask:
    name: str
    mask: np.ndarray
    evidence_status: str
    source_files: tuple[str, ...]
    source_zones: tuple[str, ...]
    risk_class: str
    design_use: str

    @property
    def pixel_count(self) -> int:
        return int(self.mask.sum())

    def report_entry(self) -> dict[str, Any]:
        return {
            "evidence_status": self.evidence_status,
            "pixel_count": self.pixel_count,
            "risk_class": self.risk_class,
            "source_files": list(self.source_files),
            "source_zones": list(self.source_zones),
            "design_use": self.design_use,
        }


def axis_fields(fields: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    pos = fields["pos"]
    axes = fields["axes"]
    length = pos[..., axes["LEN"]]
    lateral = pos[..., axes["LAT"]]
    height = pos[..., axes["HGT"]]
    symmetry = np.abs(lateral - 0.5)
    return length, lateral, height, symmetry


def mask_report_entries(masks: dict[str, StockPanelMask], names: list[str]) -> dict[str, dict[str, Any]]:
    return {name: masks[name].report_entry() for name in names}


def build_stock_panel_masks(
    fields: dict[str, Any],
    params: PremiumMaskParams | None = None,
) -> dict[str, StockPanelMask]:
    params = params or PremiumMaskParams()
    labels = fields["labels"]
    zones = fields["zones"]
    coverage = fields["coverage"]
    length, _lateral, height, symmetry = axis_fields(fields)

    body = coverage & (labels > 0)
    upper = body & (height > 0.48)
    lower = body & (height <= 0.48)
    nose = body & (length > 0.72)
    rear = body & (length < 0.36)
    deck = upper & (height > 0.58)
    engine_deck = rear & deck
    side_band = lower & (height > 0.22) & (symmetry > 0.18) & (symmetry < 0.43)

    named_masks = _named_psd_masks(labels, zones)
    masks: dict[str, StockPanelMask] = {
        name: _local_panel_mask(name, mask, source_zones, design_use)
        for name, (mask, source_zones, design_use) in named_masks.items()
    }

    spine_width = params.spine_width + 0.018 * np.clip(length - 0.68, 0, 1)
    center_spine = upper & _thin_line(symmetry, 0.0, spine_width)
    nose_spear = nose & _thin_line(symmetry, 0.0, params.spine_width * (1.35 - 0.45 * (length - 0.72)))

    blade_center = params.blade_offset + params.blade_slope * np.clip(length - 0.28, -0.12, 0.52)
    side_blade = side_band & _thin_line(symmetry, blade_center, 0.032)
    secondary_blade = side_band & _thin_line(symmetry, np.clip(blade_center + 0.075, 0.18, 0.46), 0.020)

    rear_louver_phase = ((1.0 - length) * params.rear_louver_count + symmetry * 2.6) % 1.0
    rear_louvers = engine_deck & (symmetry > 0.08) & (symmetry < 0.35) & (rear_louver_phase < 0.30)
    rear_center_glow = engine_deck & _thin_line(symmetry, 0.0, max(params.spine_width * 0.72, 0.030))

    shoulder_line = upper & (symmetry > 0.20) & (symmetry < 0.33) & _thin_line(
        height,
        0.62 + 0.18 * (length - 0.45),
        0.026,
    )
    tail_bar = rear & _thin_line(length, 0.12, 0.022) & (height > 0.30)
    mudguard_edge = masks["mudguards"].mask & (
        (symmetry > 0.31)
        | (height > 0.62)
        | (length > 0.76)
        | (length < 0.20)
    )

    gbuffer_masks = {
        "body": (body, "Whole stock atlas footprint used by the current stock generator."),
        "upper": (upper, "High body surfaces selected by HGT/Y after GBuffer projection."),
        "lower": (lower, "Low body surfaces selected by HGT/Y after GBuffer projection."),
        "center_spine": (center_spine, "Long central premium stripe aligned by LAT symmetry and LEN flow."),
        "nose_spear": (nose_spear, "Front spear selected by positive LEN and center symmetry."),
        "side_blade": (side_blade, "Lower side blade selected by side-band height and lateral symmetry."),
        "secondary_blade": (secondary_blade, "Secondary lower side blade offset from the primary blade."),
        "rear_louvers": (rear_louvers, "Rear deck louver rhythm selected by LEN/HGT/symmetry."),
        "rear_center_glow": (rear_center_glow, "Centered rear deck focal accent."),
        "shoulder_line": (shoulder_line, "Upper shoulder pinline selected by HGT/LEN/symmetry."),
        "tail_bar": (tail_bar, "Rear transverse accent selected by low LEN and HGT."),
        "mudguard_edge": (mudguard_edge, "Mudguard edge accent combining PSD mudguards and GBuffer position."),
    }
    for name, (mask, design_use) in gbuffer_masks.items():
        source_zones = masks["mudguards"].source_zones if name == "mudguard_edge" else ()
        masks[name] = _gbuffer_panel_mask(name, mask, design_use, source_zones=source_zones)

    return masks


def _named_psd_masks(
    labels: np.ndarray,
    zones: list[dict[str, Any]],
) -> dict[str, tuple[np.ndarray, tuple[str, ...], str]]:
    specs: dict[str, tuple[Callable[[str], bool], str]] = {
        "main_body_top": (
            lambda name: name.startswith("mainbodytop"),
            "Large named top body surfaces for base fields and broad graphics.",
        ),
        "main_body_under": (
            lambda name: name.startswith("mainbodyunder"),
            "Named underside body surfaces for dark material continuation.",
        ),
        "side_under_color": (
            lambda name: name.startswith("sideundercolor"),
            "Named lower side surfaces for sidepod blades and color blocks.",
        ),
        "tailwing": (
            lambda name: "tailwing" in name,
            "Named rear wing surfaces for rear identity bands.",
        ),
        "mudguards": (
            lambda name: "mudguard" in name,
            "Named mudguard surfaces for guard caps and edge pinlines.",
        ),
        "nose_part": (
            lambda name: name == "nosepart",
            "Named nose part for front identity shape.",
        ),
        "side_wings": (
            lambda name: "sidewings" in name,
            "Named side wing surfaces for small aero accents.",
        ),
        "underplate": (
            lambda name: "underplate" in name,
            "Named underplate surfaces for shadow and low detail.",
        ),
        "helmet": (
            lambda name: name.startswith("helmet_"),
            "Named helmet surfaces for restrained pilot color continuity.",
        ),
        "helmet_glass": (
            lambda name: name.startswith("helmetglass"),
            "Named visor/glass surfaces for restrained shade treatment.",
        ),
        "mirrors": (
            lambda name: "mirror" in name,
            "Named mirror surfaces for small color verification marks.",
        ),
    }

    results: dict[str, tuple[np.ndarray, tuple[str, ...], str]] = {}
    lowered_zones = [(zone, zone["name"].lower()) for zone in zones]
    for mask_name, (predicate, design_use) in specs.items():
        selected = [zone for zone, lowered in lowered_zones if predicate(lowered)]
        ids = [int(zone["id"]) for zone in selected]
        source_zones = tuple(zone["name"] for zone in selected)
        results[mask_name] = (np.isin(labels, ids), source_zones, design_use)
    return results


def _local_panel_mask(
    name: str,
    mask: np.ndarray,
    source_zones: tuple[str, ...],
    design_use: str,
) -> StockPanelMask:
    return StockPanelMask(
        name=name,
        mask=mask,
        evidence_status="proven_local_psd_parts_label_map",
        source_files=(PSD_PARTS_JSON, PSD_PARTS_LABELS),
        source_zones=source_zones,
        risk_class=_risk_class(int(mask.sum())),
        design_use=design_use,
    )


def _gbuffer_panel_mask(
    name: str,
    mask: np.ndarray,
    design_use: str,
    *,
    source_zones: tuple[str, ...] = (),
) -> StockPanelMask:
    return StockPanelMask(
        name=name,
        mask=mask,
        evidence_status="experimental_until_tmuf_smoke",
        source_files=(PSD_PARTS_JSON, PSD_PARTS_LABELS, GBUFFER_POSITION, GBUFFER_COVERAGE, GBUFFER_EXTENTS),
        source_zones=source_zones,
        risk_class=_risk_class(int(mask.sum())),
        design_use=design_use,
    )


def _thin_line(field: np.ndarray, center: np.ndarray | float, width: float) -> np.ndarray:
    return np.abs(field - center) < width


def _risk_class(area: int) -> str:
    if area >= 100_000:
        return "broad_design_surface"
    if area >= 25_000:
        return "medium_accent_surface"
    if area >= 5_000:
        return "small_detail_surface"
    return "probe_only_tiny_fragment"
