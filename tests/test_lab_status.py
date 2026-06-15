import json
from pathlib import Path
import tempfile
import unittest


class LabStatusTests(unittest.TestCase):
    def test_lab_status_summarizes_current_goal_state_without_completion(self):
        from src.evidence.lab_status import build_lab_status

        status = build_lab_status()

        self.assertEqual(status["objective_status"], "not_complete_tmuf_smoke_pending")
        self.assertIn("stock_calibration_tmuf_smoke_pending", status["goal_completion_blockers"])
        self.assertEqual(status["stock"]["tmuf_smoke_status"], "pending")
        self.assertTrue(status["stock"]["local_checks_passed"])
        self.assertEqual(status["stock"]["candidate_count"], 5)
        self.assertEqual(status["profiles"]["overall_status"], "custom_profiles_locked")
        self.assertEqual(status["smoke_kit"]["status"], "not_run")
        self.assertTrue(status["smoke_kit"]["exists"])
        self.assertIn("run_tmuf_calibration_smoke_test", status["next_required_evidence"])
        self.assertIn("record_tmuf_smoke_evidence", status["next_required_evidence"])

    def test_cli_can_emit_and_write_status_json(self):
        from recipes.lab_status import main

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "lab_status.json"
            output = main(["--json", "--write", str(out_path)])
            data = json.loads(output)

            self.assertEqual(data["objective_status"], "not_complete_tmuf_smoke_pending")
            self.assertTrue(out_path.exists())
            written = json.loads(out_path.read_text())
            self.assertEqual(written["objective_status"], data["objective_status"])


if __name__ == "__main__":
    unittest.main()
