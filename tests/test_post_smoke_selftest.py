import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class PostSmokeSelftestTests(unittest.TestCase):
    def test_synthetic_post_smoke_selftest_validates_temp_copy_without_touching_real_reports(self):
        from src.evidence.post_smoke_selftest import run_synthetic_post_smoke_selftest

        root = Path(__file__).resolve().parents[1]
        real_index = root / "out" / "reports" / "premium_batch_index.json"
        before = real_index.read_text()

        with tempfile.TemporaryDirectory() as tmp:
            result = run_synthetic_post_smoke_selftest(
                source_root=root,
                workspace_root=Path(tmp) / "synthetic_post_smoke",
            )

        after = real_index.read_text()
        self.assertEqual(after, before)

        self.assertTrue(result["synthetic_smoke"])
        self.assertFalse(result["writes_source_root"])
        self.assertFalse(result["claims_real_tmuf_proof"])
        self.assertEqual(result["stock"]["tmuf_smoke_status"], "passed")
        self.assertEqual(result["stock"]["completion_status"], "complete")
        self.assertEqual(result["profiles"]["stock_calibration_gate"], "passed")
        self.assertEqual(
            result["profiles"]["profiles"]["ch2026_fullcar"]["status"],
            "ready_for_experimental_build",
        )
        self.assertEqual(result["profiles"]["profiles"]["ch2026_nomud"]["status"], "locked")
        self.assertIn("synthetic_only_not_real_tmuf_evidence", result["limits"])
        self.assertEqual(json.loads(before)["tmuf_smoke_status"], "pending")

    def test_cli_runs_synthetic_selftest_and_prints_json(self):
        root = Path(__file__).resolve().parents[1]
        recipe = root / "recipes" / "synthetic_post_smoke_selftest.py"

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            result = subprocess.run(
                [
                    sys.executable,
                    str(recipe),
                    "--workspace",
                    str(workspace),
                    "--json",
                ],
                check=True,
                capture_output=True,
                text=True,
                cwd=root,
            )

        data = json.loads(result.stdout)
        self.assertTrue(data["synthetic_smoke"])
        self.assertFalse(data["claims_real_tmuf_proof"])
        self.assertEqual(data["stock"]["completion_status"], "complete")
        self.assertIn("synthetic_only_not_real_tmuf_evidence", data["limits"])

    def test_synthetic_selftest_refuses_unmarked_existing_workspace(self):
        from src.evidence.post_smoke_selftest import run_synthetic_post_smoke_selftest

        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()
            important = workspace / "important.txt"
            important.write_text("do not delete")

            with self.assertRaises(ValueError) as context:
                run_synthetic_post_smoke_selftest(
                    source_root=root,
                    workspace_root=workspace,
                )

            self.assertIn("refusing to remove unmarked synthetic workspace", str(context.exception))
            self.assertEqual(important.read_text(), "do not delete")


if __name__ == "__main__":
    unittest.main()
