import json
from pathlib import Path
import struct
import unittest
import zipfile

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ZIP_TIMESTAMP = (2000, 1, 1, 0, 0, 0)


def _dds_info(data: bytes) -> dict[str, object]:
    if data[:4] != b"DDS ":
        raise AssertionError("not a DDS file")
    return {
        "height": struct.unpack("<I", data[12:16])[0],
        "width": struct.unpack("<I", data[16:20])[0],
        "fourcc": data[84:88].decode("ascii", errors="replace"),
    }


class PanelFamilyProbeTests(unittest.TestCase):
    def test_panel_family_probe_generates_stock_safe_supplemental_artifact(self):
        from src.stock_diffuse.panel_probe import PANEL_PROBE_NAME, save_outputs

        outputs = save_outputs()
        self.assertEqual(outputs["name"], PANEL_PROBE_NAME)

        zip_path = Path(outputs["zip"])
        report_path = Path(outputs["report"])
        atlas_path = Path(outputs["atlas"])
        projection_path = Path(outputs["projection"])
        for path in (zip_path, report_path, atlas_path, projection_path):
            self.assertTrue(path.exists(), path)

        with zipfile.ZipFile(zip_path) as zf:
            self.assertEqual(set(zf.namelist()), {"Diffuse.dds", "Icon.dds"})
            self.assertEqual(
                {info.filename: info.date_time for info in zf.infolist()},
                {"Diffuse.dds": EXPECTED_ZIP_TIMESTAMP, "Icon.dds": EXPECTED_ZIP_TIMESTAMP},
            )
            diffuse = _dds_info(zf.read("Diffuse.dds"))
            icon = _dds_info(zf.read("Icon.dds"))

        self.assertEqual(diffuse["width"], 2048)
        self.assertEqual(diffuse["height"], 2048)
        self.assertEqual(diffuse["fourcc"], "DXT5")
        self.assertEqual(icon["fourcc"], "DXT5")

        with Image.open(atlas_path) as image:
            self.assertEqual(image.size, (2048, 2048))
            self.assertTrue(any(lo != hi for lo, hi in image.convert("RGB").getextrema()))

        report = json.loads(report_path.read_text())
        self.assertEqual(report["skin_name"], PANEL_PROBE_NAME)
        self.assertEqual(report["route"], "stock_diffuse_only")
        self.assertEqual(report["package_files"], ["Diffuse.dds", "Icon.dds"])
        self.assertEqual(report["tmuf_smoke_test"], "not_run")
        self.assertTrue(report["supplemental_smoke_artifact"])
        self.assertTrue(report["does_not_prove_tmuf_smoke"])
        self.assertEqual(report["proof_role"], "panel_family_runtime_visibility_probe")
        self.assertEqual(report["evidence_status"]["gbuffer_mapping"], "experimental_until_tmuf_smoke")
        self.assertEqual(report["evidence_status"]["tmuf_runtime_visibility"], "not_proven_until_smoke")
        self.assertEqual(report["evidence_status"]["donor_gbx"], "not_used")
        self.assertEqual(report["evidence_status"]["details_dds"], "not_used")
        self.assertEqual(report["evidence_status"]["projshad_dds"], "not_used")

        family_colors = report["panel_family_colors"]
        for family_name in (
            "front_nose_centerline",
            "cockpit_mid_deck",
            "side_flanks_aero",
            "rear_engine_tail",
            "support_auxiliary",
        ):
            self.assertIn(family_name, family_colors)
            family = report["surface_families"][family_name]
            self.assertEqual(family["tmuf_runtime_status"], "not_proven_until_smoke")
            self.assertGreater(family["pixel_count"], 0)
            self.assertTrue(family["targets"])

        generator_masks = report["generator_masks_not_catalog_panels"]
        self.assertIn("nose_spear", generator_masks)
        self.assertIn("side_blade", generator_masks)
        self.assertIn("rear_louvers", generator_masks)
        self.assertIn("rear_center_glow", generator_masks)
        self.assertEqual(generator_masks["rear_louvers"]["catalog_status"], "not_catalog_panel")
        self.assertEqual(generator_masks["rear_louvers"]["evidence_status"], "experimental_until_tmuf_smoke")

        self.assertIn("authoritative/parts/panels_high_labels.npy", report["input_evidence"])
        self.assertIn("authoritative/parts/panels_fine_labels.npy", report["input_evidence"])
        self.assertEqual(report["output_artifacts"]["skin_zip"]["path"], f"out/skins/{PANEL_PROBE_NAME}.zip")


if __name__ == "__main__":
    unittest.main()
