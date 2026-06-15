import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from PIL import Image


class SmokeKitTests(unittest.TestCase):
    def test_build_smoke_kit_collects_required_files_without_passing_gate(self):
        from src.evidence.smoke_kit import build_smoke_kit

        with tempfile.TemporaryDirectory() as tmp:
            kit = build_smoke_kit(Path(tmp) / "kit")

            manifest_path = Path(kit["manifest"])
            zip_path = Path(kit["zip"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(zip_path.exists())

            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(manifest["status"], "not_run")
            self.assertTrue(manifest["does_not_prove_tmuf_smoke"])
            self.assertEqual(manifest["calibration_skin"], "skins/calibration_stock_diffuse.zip")
            self.assertIn("proof/calibration_tmuf_smoke_template.json", manifest["files"])
            self.assertIn("previews/calibration_stock_diffuse_projected_side_top_rear.png", manifest["files"])
            self.assertIn("previews/tmuf_smoke_contact_sheet.png", manifest["files"])
            self.assertTrue(any("recipes/record_tmuf_smoke.py" in step for step in manifest["next_steps"]))

            contact_sheet = manifest_path.parent / "previews" / "tmuf_smoke_contact_sheet.png"
            self.assertTrue(contact_sheet.exists())
            with Image.open(contact_sheet) as image:
                self.assertGreaterEqual(image.width, 900)
                self.assertGreaterEqual(image.height, 600)
                self.assertTrue(any(channel_min != channel_max for channel_min, channel_max in image.convert("RGB").getextrema()))

            with zipfile.ZipFile(zip_path) as zf:
                names = set(zf.namelist())
                self.assertEqual(names, set(manifest["files"]) | {"kit_manifest.json"})
                self.assertTrue(all(info.date_time == (2000, 1, 1, 0, 0, 0) for info in zf.infolist()))

    def test_validate_smoke_kit_detects_stale_copied_files(self):
        from src.evidence.smoke_kit import build_smoke_kit, validate_smoke_kit

        with tempfile.TemporaryDirectory() as tmp:
            kit_dir = Path(tmp) / "kit"
            build_smoke_kit(kit_dir)

            fresh = validate_smoke_kit(kit_dir)
            self.assertTrue(fresh["exists"])
            self.assertTrue(fresh["fresh"])
            self.assertEqual(fresh["stale_files"], [])

            (kit_dir / "README_tmuf_smoke_test.md").write_text("stale instructions\n")

            stale = validate_smoke_kit(kit_dir)
            self.assertFalse(stale["fresh"])
            self.assertIn("README_tmuf_smoke_test.md", stale["stale_files"])

            (kit_dir / "previews" / "tmuf_smoke_contact_sheet.png").write_bytes(b"stale contact sheet\n")

            stale_contact = validate_smoke_kit(kit_dir)
            self.assertFalse(stale_contact["fresh"])
            self.assertIn("previews/tmuf_smoke_contact_sheet.png", stale_contact["stale_files"])

    def test_install_calibration_skin_requires_explicit_target_and_only_copies_skin(self):
        from src.evidence.smoke_kit import CALIBRATION_SKIN, install_calibration_skin

        with tempfile.TemporaryDirectory() as tmp:
            install_dir = Path(tmp) / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)
            result = install_calibration_skin(install_dir)

            copied = Path(result["installed_skin"])
            self.assertEqual(copied.parent, install_dir)
            self.assertEqual(copied.name, "calibration_stock_diffuse.zip")
            self.assertTrue(copied.exists())
            self.assertEqual(result["status"], "installed_not_tested")
            self.assertEqual(result["route"], "skins_vehicles_stadiumcar")
            self.assertTrue(result["does_not_prove_tmuf_smoke"])
            self.assertEqual(result["sha256"], result["source_sha256"])
            self.assertEqual(result["size_bytes"], CALIBRATION_SKIN.stat().st_size)
            self.assertEqual(
                copied.read_bytes(),
                CALIBRATION_SKIN.read_bytes(),
            )

            self.assertEqual(sorted(path.name for path in install_dir.iterdir()), ["calibration_stock_diffuse.zip"])

    def test_install_calibration_skin_rejects_missing_or_implausible_targets(self):
        from src.evidence.smoke_kit import install_calibration_skin

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "Skins" / "Vehicles" / "StadiumCar"
            with self.assertRaises(FileNotFoundError):
                install_calibration_skin(missing)
            self.assertFalse(missing.exists())

            wrong = root / "StadiumCar"
            wrong.mkdir()
            with self.assertRaises(ValueError):
                install_calibration_skin(wrong)
            self.assertEqual(list(wrong.iterdir()), [])

    def test_cli_outputs_smoke_kit_json(self):
        from recipes.prepare_tmuf_smoke_kit import main

        with tempfile.TemporaryDirectory() as tmp:
            output = main(["--out-dir", tmp, "--json"])
            data = json.loads(output)

            self.assertEqual(data["status"], "not_run")
            self.assertTrue(Path(data["manifest"]).exists())
            self.assertTrue(Path(data["zip"]).exists())


if __name__ == "__main__":
    unittest.main()
