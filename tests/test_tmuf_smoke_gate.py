import json
from pathlib import Path
import tempfile
import unittest


class TmufSmokeGateTests(unittest.TestCase):
    def test_template_is_not_a_pass_and_lists_required_observations(self):
        from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS, evaluate_smoke_report, write_template

        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "calibration_tmuf_smoke_template.json"
            write_template(template_path)

            data = json.loads(template_path.read_text())
            self.assertEqual(data["status"], "not_run")
            self.assertEqual(data["artifact"], "out/skins/calibration_stock_diffuse.zip")
            self.assertEqual(set(data["observations"]), set(REQUIRED_OBSERVATIONS))
            self.assertTrue(all(value is False for value in data["observations"].values()))

            result = evaluate_smoke_report(template_path, base_dir=Path(tmp))
            self.assertFalse(result["passed"])
            self.assertEqual(result["gbuffer_mapping_status"], "experimental_until_tmuf_smoke")
            self.assertEqual(set(result["missing_observations"]), set(REQUIRED_OBSERVATIONS))

    def test_valid_manual_evidence_can_promote_generated_reports(self):
        from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS, apply_smoke_result, evaluate_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            screenshot = base / "tmuf_calibration_front_side.png"
            screenshot.write_bytes(b"fake screenshot bytes")
            smoke_report = base / "calibration_tmuf_smoke.json"
            smoke_report.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "artifact": "out/skins/calibration_stock_diffuse.zip",
                        "status": "passed",
                        "tester": "manual tester",
                        "tmuf_build": "TMUF local install",
                        "test_date_local": "2026-06-15",
                        "screenshots": [screenshot.name],
                        "observations": {name: True for name in REQUIRED_OBSERVATIONS},
                    }
                )
            )
            generated_report = base / "black_magenta_cyan_blade.json"
            generated_report.write_text(
                json.dumps(
                    {
                        "skin_name": "black_magenta_cyan_blade",
                        "tmuf_smoke_test": "not_run",
                        "proof_gate": {"calibration_stock_diffuse": "required_before_proven_use"},
                        "evidence_status": {"gbuffer_mapping": "experimental_until_tmuf_smoke"},
                    }
                )
            )

            result = evaluate_smoke_report(smoke_report, base_dir=base)
            self.assertTrue(result["passed"])
            self.assertEqual(result["gbuffer_mapping_status"], "proven_by_tmuf_smoke")

            updated = apply_smoke_result(smoke_report, report_paths=[generated_report], base_dir=base)
            self.assertEqual(updated, [generated_report])
            promoted = json.loads(generated_report.read_text())
            self.assertEqual(promoted["tmuf_smoke_test"], "passed")
            self.assertEqual(promoted["evidence_status"]["gbuffer_mapping"], "proven_by_tmuf_smoke")
            self.assertEqual(promoted["proof_gate"]["calibration_stock_diffuse"], "passed")
            self.assertEqual(promoted["tmuf_smoke_evidence"]["screenshots"], [screenshot.name])

    def test_missing_screenshot_prevents_promotion(self):
        from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS, apply_smoke_result, evaluate_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            smoke_report = base / "calibration_tmuf_smoke.json"
            smoke_report.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "artifact": "out/skins/calibration_stock_diffuse.zip",
                        "status": "passed",
                        "tester": "manual tester",
                        "tmuf_build": "TMUF local install",
                        "test_date_local": "2026-06-15",
                        "screenshots": ["missing.png"],
                        "observations": {name: True for name in REQUIRED_OBSERVATIONS},
                    }
                )
            )

            result = evaluate_smoke_report(smoke_report, base_dir=base)
            self.assertFalse(result["passed"])
            self.assertEqual(result["missing_screenshots"], ["missing.png"])
            with self.assertRaises(ValueError):
                apply_smoke_result(smoke_report, report_paths=[], base_dir=base)


if __name__ == "__main__":
    unittest.main()
