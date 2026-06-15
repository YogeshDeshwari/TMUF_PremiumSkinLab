import json
import unittest


class StockValidatorTests(unittest.TestCase):
    def test_current_stock_outputs_pass_local_checks_but_keep_smoke_pending(self):
        from src.evidence.stock_validator import REQUIRED_STOCK_SKINS, validate_stock_outputs

        result = validate_stock_outputs()

        self.assertTrue(result["local_checks_passed"])
        self.assertEqual(result["completion_status"], "not_complete_tmuf_smoke_pending")
        self.assertEqual(result["tmuf_smoke_status"], "pending")
        self.assertEqual(result["errors"], [])
        self.assertIn("tmuf_smoke_pending", result["warnings"])
        self.assertEqual([skin["skin_name"] for skin in result["skins"]], REQUIRED_STOCK_SKINS)

        for skin in result["skins"]:
            checks = skin["checks"]
            self.assertTrue(checks["zip_exists"])
            self.assertTrue(checks["zip_stock_diffuse_only"])
            self.assertTrue(checks["zip_has_stable_timestamps"])
            self.assertTrue(checks["dds_headers_valid"])
            self.assertTrue(checks["report_exists"])
            self.assertTrue(checks["report_route_stock_diffuse_only"])
            self.assertTrue(checks["report_declares_no_donor_or_details_route"])
            self.assertTrue(checks["report_input_evidence_matches_manifest"])
            self.assertTrue(checks["atlas_preview_exists"])
            self.assertTrue(checks["projection_preview_exists"])
            self.assertTrue(checks["preview_visual_quality_passed"])
            self.assertFalse(checks["tmuf_smoke_passed"])
            self.assertIn("visual_metrics", skin)

    def test_report_input_evidence_must_match_manifest(self):
        from src.evidence.input_trace import STOCK_DIFFUSE_INPUTS
        from src.evidence.stock_validator import validate_input_evidence

        manifest = {
            "resources": [
                {
                    "path": path,
                    "evidence_label": "proven",
                    "sha256": f"{index:064x}",
                    "size_bytes": index + 1,
                }
                for index, path in enumerate(STOCK_DIFFUSE_INPUTS)
            ]
        }
        report = {"input_evidence": {}}

        errors = validate_input_evidence(report, manifest)

        self.assertEqual(len(errors), len(STOCK_DIFFUSE_INPUTS))
        self.assertTrue(all(error.startswith("missing input evidence:") for error in errors))

        report["input_evidence"] = {
            path: {
                "evidence_label": entry["evidence_label"],
                "sha256": entry["sha256"],
                "size_bytes": entry["size_bytes"],
            }
            for path, entry in [(item["path"], item) for item in manifest["resources"]]
        }
        self.assertEqual(validate_input_evidence(report, manifest), [])

        first = STOCK_DIFFUSE_INPUTS[0]
        report["input_evidence"][first]["sha256"] = "bad"
        self.assertEqual(
            validate_input_evidence(report, manifest),
            [f"input evidence sha256 mismatch: {first}"],
        )

    def test_cli_outputs_json_summary(self):
        from recipes.validate_stock_outputs import main

        output = main(["--json"])
        data = json.loads(output)

        self.assertTrue(data["local_checks_passed"])
        self.assertEqual(data["tmuf_smoke_status"], "pending")


if __name__ == "__main__":
    unittest.main()
