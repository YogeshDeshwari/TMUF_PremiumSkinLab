from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_dilation, distance_transform_edt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "dds"))
from tmnf_dds import build_dds_dxt5_bytes  # noqa: E402
from src.stock_diffuse.package import write_stable_zip_entry  # noqa: E402


SIZE = 2048
GBUFFER_DIR = ROOT / "resources" / "authoritative" / "gbuffer"
PARTS_DIR = ROOT / "resources" / "authoritative" / "parts"
REF_DIR = ROOT / "resources" / "authoritative" / "reference"
SKIN_NAME = "calibration_stock_diffuse"


def hx(value: str) -> np.ndarray:
    value = value.lstrip("#")
    return np.array([int(value[i : i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def load_fields() -> dict[str, Any]:
    pos = np.load(GBUFFER_DIR / "position_2048.npy")
    coverage = np.load(GBUFFER_DIR / "coverage_2048.npy") > 0
    labels = np.load(PARTS_DIR / "psd_parts_labels.npy")
    zones = json.loads((PARTS_DIR / "psd_parts.json").read_text())["zones"]
    axes = json.loads((GBUFFER_DIR / "extents_2048.json").read_text())["axis_roles"]

    footprint = labels > 0
    if (footprint & ~coverage).any():
        nearest = distance_transform_edt(~coverage, return_indices=True)[1]
        pos = pos[tuple(nearest)]
        coverage = footprint

    return {"pos": pos, "coverage": coverage, "labels": labels, "zones": zones, "axes": axes}


def mudguard_ids(zones: list[dict[str, Any]]) -> list[int]:
    return [z["id"] for z in zones if "mudguard" in z["name"].lower()]


def build_calibration_rgba() -> Image.Image:
    fields = load_fields()
    pos = fields["pos"]
    coverage = fields["coverage"]
    labels = fields["labels"]
    axes = fields["axes"]

    length = pos[..., axes["LEN"]]
    lateral = pos[..., axes["LAT"]]
    height = pos[..., axes["HGT"]]
    symmetry = np.abs(lateral - 0.5)

    rgb = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    alpha = np.full((SIZE, SIZE), 113, dtype=np.float32)

    rgb[coverage] = hx("#101014")
    rgb[coverage & (lateral < 0.42)] = hx("#00b050")
    rgb[coverage & (lateral > 0.58)] = hx("#ffd400")
    rgb[coverage & (length > 0.82)] = hx("#e02020")
    rgb[coverage & (length < 0.18)] = hx("#2050ff")
    rgb[coverage & (height > 0.74)] = hx("#f0f0f0")
    rgb[coverage & (height < 0.22)] = hx("#050507")

    centerline = coverage & (symmetry < 0.035)
    rgb[centerline] = hx("#00d4ff")
    alpha[centerline] = 150

    mudguards = np.isin(labels, mudguard_ids(fields["zones"]))
    rgb[mudguards] = hx("#ff00c8")
    alpha[mudguards] = 150

    seams = binary_dilation(
        ((labels != np.roll(labels, 1, 0)) | (labels != np.roll(labels, 1, 1))) & (labels > 0),
        iterations=1,
    )
    rgb[seams] *= 0.45

    ao_path = REF_DIR / "official_prelight_AO.png"
    if ao_path.exists():
        ao = np.asarray(Image.open(ao_path).convert("L").resize((SIZE, SIZE)), dtype=np.float32)
        rgb *= (0.68 + 0.32 * ao / 255.0)[..., None]

    out = np.zeros((SIZE, SIZE, 4), dtype=np.uint8)
    out[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(alpha, 0, 255).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def project_view(rgba: np.ndarray, plane: str, fields: dict[str, Any]) -> Image.Image:
    pos = fields["pos"]
    coverage = fields["coverage"]
    axes = fields["axes"]
    length = pos[..., axes["LEN"]]
    lateral = pos[..., axes["LAT"]]
    height = pos[..., axes["HGT"]]
    rgb = rgba[..., :3]

    if plane == "rear":
        selected = coverage & (length < 0.34)
        u, v, depth = lateral, 1.0 - height, -length
        width, canvas_height = 480, 360
    elif plane == "top":
        selected = coverage
        u, v, depth = length, lateral, height
        width, canvas_height = 900, 460
    else:
        selected = coverage & (lateral >= 0.5)
        u, v, depth = length, 1.0 - height, lateral
        width, canvas_height = 900, 360

    yy, xx = np.where(selected)
    if yy.size == 0:
        return Image.new("RGB", (width, canvas_height), (18, 18, 22))

    uu, vv, dd = u[selected], v[selected], depth[selected]
    px = ((uu - uu.min()) / (np.ptp(uu) + 1e-9) * (width - 1)).astype(int)
    py = ((vv - vv.min()) / (np.ptp(vv) + 1e-9) * (canvas_height - 1)).astype(int)
    order = np.argsort(dd)
    img = np.full((canvas_height, width, 3), 18, dtype=np.uint8)
    img[py[order], px[order]] = rgb[yy, xx][order]
    return Image.fromarray(img, "RGB")


def save_outputs() -> Path:
    out_skin = ROOT / "out" / "skins" / f"{SKIN_NAME}.zip"
    out_preview = ROOT / "out" / "previews" / f"{SKIN_NAME}_projected_side_top_rear.png"
    out_atlas = ROOT / "out" / "previews" / f"{SKIN_NAME}_atlas.png"
    out_report = ROOT / "out" / "reports" / f"{SKIN_NAME}.json"
    for path in (out_skin.parent, out_preview.parent, out_report.parent):
        path.mkdir(parents=True, exist_ok=True)

    image = build_calibration_rgba()
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
    draw = ImageDraw.Draw(canvas)
    draw.text((pad, 2), "side", fill=(230, 230, 240))
    draw.text((pad, pad + side.height + 2), "top", fill=(230, 230, 240))
    draw.text((pad * 2 + side.width, 2), "rear", fill=(230, 230, 240))
    canvas.save(out_preview)

    report = {
        "skin_name": SKIN_NAME,
        "route": "stock_diffuse_only",
        "package_files": ["Diffuse.dds", "Icon.dds"],
        "tmuf_smoke_test": "not_run",
        "evidence_status": {
            "stock_diffuse_route": "proven_by_local_docs_and_package_contract",
            "gbuffer_mapping": "experimental_until_tmuf_smoke",
            "dds_package": "generated_and_header_checked_by_tests",
        },
        "calibration_colors": {
            "nose": "red",
            "tail": "blue",
            "left": "green",
            "right": "yellow",
            "roof_high": "white",
            "lower_floor": "dark",
            "mudguards": "magenta",
            "centerline": "cyan",
        },
        "known_risks": [
            "GBuffer direction and nearest-neighbour footprint fill require TMUF visual confirmation.",
            "Diffuse alpha is kept conservative; gloss behavior is not considered proven by this artifact.",
        ],
    }
    out_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return out_skin


def main() -> int:
    out = save_outputs()
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
