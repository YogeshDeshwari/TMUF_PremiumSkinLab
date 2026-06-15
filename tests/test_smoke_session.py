import json
from pathlib import Path
import tempfile
import unittest


class SmokeSessionTests(unittest.TestCase):
    def test_smoke_session_creates_exact_capture_paths_without_fake_screenshots(self):
        from src.evidence.smoke_gate import REQUIRED_SCREENSHOT_ROLES
        from src.evidence.smoke_kit import install_calibration_skin, write_install_receipt
        from src.evidence.smoke_session import build_smoke_session

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_dir = root / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)
            receipt = write_install_receipt(
                install_calibration_skin(install_dir),
                root / "out" / "proof" / "tmuf_calibration_smoke_kit",
            )
            session_dir = root / "out" / "proof" / "tmuf_smoke_session"

            manifest = build_smoke_session(
                session_dir,
                base_dir=root,
                install_receipt=receipt,
                output_path=root / "out" / "proof" / "calibration_tmuf_smoke.json",
            )

            self.assertEqual(manifest["status"], "awaiting_tmuf_screenshots")
            self.assertTrue(manifest["does_not_prove_tmuf_smoke"])
            self.assertTrue(manifest["install_receipt_valid"])
            self.assertEqual([slot["role"] for slot in manifest["screenshot_slots"]], REQUIRED_SCREENSHOT_ROLES)
            for slot in manifest["screenshot_slots"]:
                self.assertFalse(slot["exists"])
                self.assertFalse(Path(slot["path"]).exists())
                self.assertTrue(slot["path"].endswith(f"tmuf_calibration_{slot['role']}.png"))
            self.assertIn("recipes/record_tmuf_smoke.py", manifest["record_command"])
            self.assertIn("--all-required-observations-passed", manifest["record_command"])
            self.assertIn("--install-receipt", manifest["record_command"])
            self.assertTrue((session_dir / "session_manifest.json").exists())
            self.assertTrue((session_dir / "record_tmuf_smoke_command.txt").exists())
            self.assertTrue((session_dir / "README_tmuf_smoke_session.md").exists())
            self.assertEqual(
                json.loads((session_dir / "session_manifest.json").read_text())["record_command"],
                manifest["record_command"],
            )

    def test_smoke_session_cli_emits_json(self):
        from recipes.prepare_tmuf_smoke_session import main

        with tempfile.TemporaryDirectory() as tmp:
            session_dir = Path(tmp) / "session"
            missing_receipt = Path(tmp) / "missing_receipt.json"
            output = main([
                "--session-dir",
                str(session_dir),
                "--install-receipt",
                str(missing_receipt),
                "--json",
            ])
            data = json.loads(output)

            self.assertEqual(data["status"], "awaiting_tmuf_screenshots")
            self.assertTrue(session_dir.exists())
            self.assertEqual(data["session_dir"], str(session_dir))
            self.assertFalse(data["install_receipt_valid"])
            self.assertIn("missing_install_receipt", data["install_receipt_errors"])


if __name__ == "__main__":
    unittest.main()
