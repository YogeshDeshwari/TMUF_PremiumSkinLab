from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


ATLAS_NONBLANK_MIN = 0.50
PROJECTION_NONBLANK_MIN = 0.50
CONTRAST_MIN = 60.0
ACCENT_RATIO_MIN = 0.02
LARGEST_ACCENT_COMPONENT_MIN = 50000


def _image_metrics(path: Path) -> dict[str, float | int]:
    img = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    lum = img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722
    nonblank = float((lum > 8).mean())
    contrast = float(np.percentile(lum, 95) - np.percentile(lum, 5))
    magenta = (img[..., 0] > 135) & (img[..., 2] > 105) & (img[..., 1] < 95)
    cyan = (img[..., 1] > 110) & (img[..., 2] > 130) & (img[..., 0] < 95)
    accent = magenta | cyan

    labels, count = ndimage.label(accent)
    if count:
        sizes = np.bincount(labels.ravel())
        largest_component = int(sizes[1:].max()) if sizes.size > 1 else 0
    else:
        largest_component = 0

    return {
        "nonblank_ratio": round(nonblank, 6),
        "contrast": round(contrast, 6),
        "magenta_ratio": round(float(magenta.mean()), 6),
        "cyan_ratio": round(float(cyan.mean()), 6),
        "largest_accent_component_pixels": largest_component,
    }


def validate_visual_quality(root: Path, skin_name: str, premium: bool) -> tuple[dict[str, bool], dict[str, float | int], list[str]]:
    root = Path(root)
    atlas_path = root / "out" / "previews" / f"{skin_name}_atlas.png"
    projection_path = root / "out" / "previews" / f"{skin_name}_projected_side_top_rear.png"
    checks = {
        "preview_visual_quality_passed": False,
        "premium_style_quality_passed": not premium,
    }
    metrics: dict[str, float | int] = {
        "atlas_nonblank_ratio": 0.0,
        "projection_nonblank_ratio": 0.0,
        "atlas_contrast": 0.0,
        "projection_contrast": 0.0,
        "atlas_magenta_ratio": 0.0,
        "atlas_cyan_ratio": 0.0,
        "largest_accent_component_pixels": 0,
    }
    errors: list[str] = []

    if not atlas_path.exists():
        errors.append(f"missing atlas preview: {atlas_path}")
        return checks, metrics, errors
    if not projection_path.exists():
        errors.append(f"missing projection preview: {projection_path}")
        return checks, metrics, errors

    atlas = _image_metrics(atlas_path)
    projection = _image_metrics(projection_path)
    metrics.update(
        {
            "atlas_nonblank_ratio": atlas["nonblank_ratio"],
            "projection_nonblank_ratio": projection["nonblank_ratio"],
            "atlas_contrast": atlas["contrast"],
            "projection_contrast": projection["contrast"],
            "atlas_magenta_ratio": atlas["magenta_ratio"],
            "atlas_cyan_ratio": atlas["cyan_ratio"],
            "largest_accent_component_pixels": atlas["largest_accent_component_pixels"],
        }
    )

    preview_passed = True
    if metrics["atlas_nonblank_ratio"] < ATLAS_NONBLANK_MIN:
        errors.append(f"atlas preview appears blank/too sparse: {skin_name}")
        preview_passed = False
    if metrics["projection_nonblank_ratio"] < PROJECTION_NONBLANK_MIN:
        errors.append(f"projection preview appears blank/too sparse: {skin_name}")
        preview_passed = False
    if metrics["atlas_contrast"] < CONTRAST_MIN:
        errors.append(f"atlas preview contrast too low: {skin_name}")
        preview_passed = False
    if metrics["projection_contrast"] < CONTRAST_MIN:
        errors.append(f"projection preview contrast too low: {skin_name}")
        preview_passed = False
    checks["preview_visual_quality_passed"] = preview_passed

    if premium:
        premium_passed = True
        if metrics["atlas_magenta_ratio"] < ACCENT_RATIO_MIN:
            errors.append(f"magenta accent ratio too low: {skin_name}")
            premium_passed = False
        if metrics["atlas_cyan_ratio"] < ACCENT_RATIO_MIN:
            errors.append(f"cyan accent ratio too low: {skin_name}")
            premium_passed = False
        if metrics["largest_accent_component_pixels"] < LARGEST_ACCENT_COMPONENT_MIN:
            errors.append(f"largest accent component too small: {skin_name}")
            premium_passed = False
        checks["premium_style_quality_passed"] = premium_passed

    return checks, metrics, errors
