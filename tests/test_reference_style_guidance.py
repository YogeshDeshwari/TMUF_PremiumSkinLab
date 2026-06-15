import json
from pathlib import Path
import tempfile
import unittest


class ReferenceStyleGuidanceTests(unittest.TestCase):
    def test_guidance_builder_extracts_black_magenta_cyan_reference_rules(self):
        from src.evidence.reference_style_guidance import build_reference_style_guidance

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports_dir = root / "reports"
            reports_dir.mkdir()
            bloom = reports_dir / "CH_Bloom_report.json"
            cyan = reports_dir / "Aqua_report.json"
            red = reports_dir / "Red_report.json"
            bloom.write_text(
                json.dumps(
                    {
                        "package_name": "CH_Bloom_Wheel_LED_Underglow.zip",
                        "package_route": "custom_fullcar_ch2026_reference",
                        "stock_lane_status": "not_stock_diffuse_only",
                        "style_metrics": {
                            "primary_livery_slot": "Diffuse.dds",
                            "dominant_palette_tags": ["black", "magenta", "blue"],
                            "slots": {
                                "Diffuse.dds": {
                                    "black_ratio": 0.13,
                                    "magenta_ratio": 0.36,
                                    "cyan_ratio": 0.04,
                                    "red_ratio": 0.0,
                                    "mean_contrast": 58.0,
                                    "alpha_visible_ratio": 1.0,
                                }
                            },
                        },
                    }
                )
            )
            cyan.write_text(
                json.dumps(
                    {
                        "package_name": "Aqua-Public-SKIN_by_MINA_TM.zip",
                        "package_route": "custom_fullcar_ch2026_reference",
                        "stock_lane_status": "not_stock_diffuse_only",
                        "style_metrics": {
                            "primary_livery_slot": "Diffuse.dds",
                            "dominant_palette_tags": ["black", "cyan", "gray"],
                            "slots": {
                                "Diffuse.dds": {
                                    "black_ratio": 0.34,
                                    "magenta_ratio": 0.0,
                                    "cyan_ratio": 0.11,
                                    "red_ratio": 0.0,
                                    "mean_contrast": 61.0,
                                    "alpha_visible_ratio": 0.0,
                                }
                            },
                        },
                    }
                )
            )
            red.write_text(
                json.dumps(
                    {
                        "package_name": "Red-Public-SKIN_by_MINA_TM.zip",
                        "package_route": "custom_fullcar_ch2026_reference",
                        "stock_lane_status": "not_stock_diffuse_only",
                        "style_metrics": {
                            "primary_livery_slot": "Diffuse.dds",
                            "dominant_palette_tags": ["black", "red", "gray"],
                            "slots": {
                                "Diffuse.dds": {
                                    "black_ratio": 0.39,
                                    "magenta_ratio": 0.0,
                                    "cyan_ratio": 0.0,
                                    "red_ratio": 0.13,
                                    "mean_contrast": 62.0,
                                    "alpha_visible_ratio": 0.0,
                                }
                            },
                        },
                    }
                )
            )
            index = root / "reference_package_index.json"
            index.write_text(
                json.dumps(
                    {
                        "schema": "tmuf_premium_skin_lab.reference_package_index.v1",
                        "route_counts": {"custom_fullcar_ch2026_reference": 3},
                        "palette_tag_counts": {"black": 3, "magenta": 1, "cyan": 1, "red": 1, "gray": 2},
                        "reports": [
                            {"report": str(bloom)},
                            {"report": str(cyan)},
                            {"report": str(red)},
                        ],
                    }
                )
            )

            guidance = build_reference_style_guidance(index)

        self.assertEqual(guidance["schema"], "tmuf_premium_skin_lab.reference_style_guidance.v1")
        self.assertTrue(guidance["does_not_prove_tmuf_smoke"])
        self.assertEqual(guidance["source_index"], str(index))
        self.assertEqual(guidance["palette_tag_counts"]["black"], 3)
        self.assertEqual(guidance["closest_black_magenta_cyan_references"][0]["package_name"], "CH_Bloom_Wheel_LED_Underglow.zip")
        self.assertEqual(guidance["closest_black_magenta_cyan_references"][0]["package_route"], "custom_fullcar_ch2026_reference")
        self.assertIn("black_gray_white_base", guidance["recommended_stock_design_rules"])
        self.assertIn("magenta_high_value_accent", guidance["recommended_stock_design_rules"])
        self.assertIn("cyan_secondary_contrast", guidance["recommended_stock_design_rules"])
        self.assertIn("red_separate_lane_not_first_bmc_family", guidance["recommended_stock_design_rules"])

    def test_current_premium_reports_carry_reference_guidance(self):
        root = Path(__file__).resolve().parents[1]
        guidance_path = root / "out" / "reports" / "reference_style_guidance.json"
        batch_path = root / "out" / "reports" / "premium_batch_index.json"

        self.assertTrue(guidance_path.exists())
        guidance = json.loads(guidance_path.read_text())
        self.assertTrue(guidance["does_not_prove_tmuf_smoke"])
        self.assertIn("CH_Bloom_Wheel_LED_Underglow.zip", {item["package_name"] for item in guidance["closest_black_magenta_cyan_references"]})

        batch = json.loads(batch_path.read_text())
        self.assertEqual(batch["reference_style_guidance"]["path"], "out/reports/reference_style_guidance.json")
        self.assertTrue(batch["reference_style_guidance"]["does_not_prove_tmuf_smoke"])
        for candidate in batch["candidates"]:
            block = candidate["reference_style_guidance"]
            self.assertEqual(block["path"], "out/reports/reference_style_guidance.json")
            self.assertIn("magenta_high_value_accent", block["applied_rules"])

        calibration = json.loads((root / "out" / "reports" / "calibration_stock_diffuse.json").read_text())
        self.assertNotIn("reference_style_guidance", calibration)


if __name__ == "__main__":
    unittest.main()
