import json
from pathlib import Path
import tempfile
import unittest
import zipfile


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

            with zipfile.ZipFile(zip_path) as zf:
                names = set(zf.namelist())
                self.assertEqual(names, set(manifest["files"]) | {"kit_manifest.json"})
                self.assertTrue(all(info.date_time == (2000, 1, 1, 0, 0, 0) for info in zf.infolist()))

    def test_install_calibration_skin_requires_explicit_target_and_only_copies_skin(self):
        from src.evidence.smoke_kit import install_calibration_skin

        with tempfile.TemporaryDirectory() as tmp:
            install_dir = Path(tmp) / "StadiumCar"
            result = install_calibration_skin(install_dir)

            copied = Path(result["installed_skin"])
            self.assertEqual(copied.parent, install_dir)
            self.assertEqual(copied.name, "calibration_stock_diffuse.zip")
            self.assertTrue(copied.exists())
            self.assertEqual(result["status"], "installed_not_tested")
            self.assertTrue(result["does_not_prove_tmuf_smoke"])
            self.assertEqual(
                copied.read_bytes(),
                (Path(__file__).resolve().parents[1] / "out" / "skins" / "calibration_stock_diffuse.zip").read_bytes(),
            )

            self.assertEqual(sorted(path.name for path in install_dir.iterdir()), ["calibration_stock_diffuse.zip"])

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
