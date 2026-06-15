import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class ReferencePackageAnalysisTests(unittest.TestCase):
    def test_custom_fullcar_reference_package_is_classified_and_previewed(self):
        from src.dds.tmnf_dds import build_dds_dxt1_bytes, build_dds_dxt5_bytes
        from src.evidence.reference_package_analysis import analyze_reference_package

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            donor_zip = root / "donor.zip"
            package_zip = root / "CH_Test.zip"
            output_dir = root / "out" / "reference_analysis"
            main_body = b"main-body-gbx"
            main_body_high = b"main-body-high-gbx"

            with zipfile.ZipFile(donor_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("MainBody.Solid.Gbx", main_body)
                zf.writestr("MainBodyHigh.Solid.Gbx", main_body_high)
            with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("Diffuse.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (20, 40, 220, 255))))
                zf.writestr("Details.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (220, 40, 180, 255))))
                zf.writestr("Icon.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (20, 220, 240, 255))))
                zf.writestr("ProjShad.dds", build_dds_dxt1_bytes(Image.new("RGBA", (8, 8), (0, 240, 255, 255))))
                zf.writestr("DiffuseDirty.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (8, 8, 8, 255))))
                zf.writestr("DetailsDirty.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (12, 12, 12, 255))))
                zf.writestr("MainBody.Solid.Gbx", main_body)
                zf.writestr("MainBodyHigh.Solid.Gbx", main_body_high)
                zf.writestr("skin.json", json.dumps({"theme": "test_theme", "finish": "GLOSS"}))

            report = analyze_reference_package(package_zip, output_dir=output_dir, donor_zip=donor_zip)

            self.assertEqual(report["schema"], "tmuf_premium_skin_lab.reference_package_analysis.v1")
            self.assertEqual(report["package_route"], "custom_fullcar_ch2026_reference")
            self.assertEqual(report["stock_lane_status"], "not_stock_diffuse_only")
            self.assertTrue(report["does_not_prove_tmuf_smoke"])
            self.assertEqual(report["skin_json"]["theme"], "test_theme")
            self.assertEqual(report["dds"]["Diffuse.dds"]["width"], 8)
            self.assertEqual(report["dds"]["Details.dds"]["fourcc"], "DXT5")
            self.assertEqual(report["dds"]["ProjShad.dds"]["fourcc"], "DXT1")
            self.assertTrue(report["donor_mesh_match"]["MainBody.Solid.Gbx"])
            self.assertTrue(report["donor_mesh_match"]["MainBodyHigh.Solid.Gbx"])
            self.assertTrue((output_dir / "CH_Test_report.json").exists())
            self.assertTrue((output_dir / "CH_Test_contact_sheet.png").exists())

    def test_reference_report_records_texture_style_metrics(self):
        from src.dds.tmnf_dds import build_dds_dxt5_bytes
        from src.evidence.reference_package_analysis import analyze_reference_package

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_zip = root / "style_metrics.zip"
            with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("Diffuse.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (0, 220, 255, 255))))
                zf.writestr("Details.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (255, 0, 180, 255))))
                zf.writestr("Icon.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (20, 20, 20, 255))))
                zf.writestr("MainBody.Solid.Gbx", b"custom-main")
                zf.writestr("MainBodyHigh.Solid.Gbx", b"custom-high")

            report = analyze_reference_package(package_zip, output_dir=root / "out")

            self.assertEqual(
                report["style_metrics"]["schema"],
                "tmuf_premium_skin_lab.reference_style_metrics.v1",
            )
            self.assertEqual(report["style_metrics"]["primary_livery_slot"], "Details.dds")
            self.assertGreater(report["style_metrics"]["slots"]["Diffuse.dds"]["cyan_ratio"], 0.8)
            self.assertGreater(report["style_metrics"]["slots"]["Details.dds"]["magenta_ratio"], 0.8)
            self.assertIn("cyan", report["style_metrics"]["dominant_palette_tags"])
            self.assertIn("magenta", report["style_metrics"]["dominant_palette_tags"])
            self.assertTrue(report["style_metrics"]["does_not_prove_tmuf_smoke"])

    def test_style_metrics_preserve_rgb_when_alpha_is_transparent(self):
        from src.dds.tmnf_dds import build_dds_dxt5_bytes
        from src.evidence.reference_package_analysis import analyze_reference_package

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_zip = root / "transparent_rgb.zip"
            with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    "Diffuse.dds",
                    build_dds_dxt5_bytes(Image.new("RGBA", (512, 512), (255, 0, 180, 0))),
                )
                zf.writestr("Icon.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (20, 20, 20, 255))))

            report = analyze_reference_package(package_zip, output_dir=root / "out")
            diffuse = report["style_metrics"]["slots"]["Diffuse.dds"]

            self.assertEqual(diffuse["alpha_visible_ratio"], 0.0)
            self.assertGreater(diffuse["magenta_ratio"], 0.8)
            self.assertLess(diffuse["black_ratio"], 0.1)

    def test_alpha_diagnostic_sheet_exposes_rgb_and_alpha_separately(self):
        from src.dds.tmnf_dds import build_dds_dxt5_bytes
        from src.evidence.reference_package_analysis import analyze_reference_package

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_zip = root / "transparent_rgb.zip"
            output_dir = root / "out"
            with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    "Diffuse.dds",
                    build_dds_dxt5_bytes(Image.new("RGBA", (512, 512), (255, 0, 180, 0))),
                )
                zf.writestr("Icon.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (20, 20, 20, 255))))

            report = analyze_reference_package(package_zip, output_dir=output_dir)

            diagnostic_path = Path(report["output_artifacts"]["alpha_diagnostic_sheet"])
            self.assertTrue(diagnostic_path.exists())
            self.assertEqual(
                report["style_metrics"]["slots"]["Diffuse.dds"]["preview_policy"],
                "rgb_and_alpha_recorded_separately",
            )
            diagnostic = Image.open(diagnostic_path).convert("RGB")
            raw_rgb_sample = diagnostic.getpixel((40, 58))
            alpha_sample = diagnostic.getpixel((302, 58))
            self.assertGreater(raw_rgb_sample[0], 200)
            self.assertLess(raw_rgb_sample[1], 50)
            self.assertGreater(raw_rgb_sample[2], 120)
            self.assertLess(max(alpha_sample), 10)

    def test_stock_diffuse_only_reference_package_stays_separate(self):
        from src.dds.tmnf_dds import build_dds_dxt5_bytes
        from src.evidence.reference_package_analysis import analyze_reference_package

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_zip = root / "stockish.zip"
            with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("Diffuse.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (0, 220, 255, 255))))
                zf.writestr("Icon.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (255, 0, 180, 255))))

            report = analyze_reference_package(package_zip, output_dir=root / "out")

            self.assertEqual(report["package_route"], "stock_diffuse_only_reference")
            self.assertEqual(report["stock_lane_status"], "reference_only_not_generated_by_lab")
            self.assertTrue(report["does_not_prove_tmuf_smoke"])

    def test_lowercase_custom_texture_names_are_classified_with_case_notes(self):
        from src.dds.tmnf_dds import build_dds_dxt5_bytes
        from src.evidence.reference_package_analysis import analyze_reference_package

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            donor_zip = root / "donor.zip"
            package_zip = root / "custom_case_variant.zip"
            with zipfile.ZipFile(donor_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("MainBody.Solid.Gbx", b"donor-main")
                zf.writestr("MainBodyHigh.Solid.Gbx", b"donor-high")
            with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("diffuse.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (10, 20, 30, 255))))
                zf.writestr("details.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (40, 50, 60, 255))))
                zf.writestr("Icon.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (70, 80, 90, 255))))
                zf.writestr("MainBody.Solid.Gbx", b"other-main")
                zf.writestr("MainBodyHigh.Solid.Gbx", b"other-high")

            report = analyze_reference_package(package_zip, output_dir=root / "out", donor_zip=donor_zip)

            self.assertEqual(report["package_route"], "custom_fullcar_other_mesh_reference")
            self.assertFalse(report["donor_mesh_match"]["MainBody.Solid.Gbx"])
            self.assertTrue(report["filename_case_notes"])
            self.assertEqual(report["filename_case_notes"][0]["entry"], "diffuse.dds")

    def test_cli_writes_reference_package_index(self):
        from src.dds.tmnf_dds import build_dds_dxt5_bytes

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_zip = root / "sample.zip"
            output_dir = root / "analysis"
            with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("Diffuse.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (0, 220, 255, 255))))
                zf.writestr("Icon.dds", build_dds_dxt5_bytes(Image.new("RGBA", (8, 8), (255, 0, 180, 255))))

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "recipes" / "analyze_reference_packages.py"),
                    "--output-dir",
                    str(output_dir),
                    str(package_zip),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("reference_package_index.json", result.stdout)
            self.assertIn("reference_package_gallery.png", result.stdout)
            self.assertIn("reference_livery_atlas_gallery.png", result.stdout)
            self.assertIn("sample_alpha_diagnostic.png", result.stdout)
            index = json.loads((output_dir / "reference_package_index.json").read_text())
            self.assertEqual(index["schema"], "tmuf_premium_skin_lab.reference_package_index.v1")
            self.assertEqual(index["reports"][0]["package_route"], "stock_diffuse_only_reference")
            self.assertEqual(index["route_counts"], {"stock_diffuse_only_reference": 1})
            self.assertIn("cyan", index["palette_tag_counts"])
            self.assertEqual(index["reports"][0]["primary_livery_slot"], "Diffuse.dds")
            self.assertEqual(index["gallery"], str(output_dir / "reference_package_gallery.png"))
            self.assertEqual(index["livery_atlas_gallery"], str(output_dir / "reference_livery_atlas_gallery.png"))
            self.assertEqual(index["reports"][0]["alpha_diagnostic_sheet"], str(output_dir / "sample_alpha_diagnostic.png"))
            self.assertTrue((output_dir / "reference_package_gallery.png").exists())
            self.assertTrue((output_dir / "reference_livery_atlas_gallery.png").exists())
            self.assertTrue((output_dir / "sample_alpha_diagnostic.png").exists())

    def test_reference_gallery_prefers_livery_texture_over_icon_or_shadow(self):
        from src.dds.tmnf_dds import build_dds_dxt1_bytes, build_dds_dxt5_bytes
        from src.evidence.reference_package_analysis import _representative_preview

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package_zip = root / "icon_heavy.zip"
            icon = Image.new("RGBA", (64, 64), (0, 0, 0, 255))
            icon_pixels = icon.load()
            for y in range(icon.height):
                for x in range(icon.width):
                    if (x // 4 + y // 4) % 2:
                        icon_pixels[x, y] = (255, 255, 255, 255)
            with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(
                    "Diffuse.dds",
                    build_dds_dxt5_bytes(Image.new("RGBA", (64, 64), (30, 90, 220, 255))),
                )
                zf.writestr("Icon.dds", build_dds_dxt5_bytes(icon))
                zf.writestr("ProjShad.dds", build_dds_dxt1_bytes(icon))

            preview = _representative_preview(package_zip)

            self.assertEqual(preview._tmuf_source_name, "Diffuse.dds")


if __name__ == "__main__":
    unittest.main()
