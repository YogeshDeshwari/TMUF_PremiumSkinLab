import json
from pathlib import Path
import tempfile
import unittest


class SmokeReadinessTests(unittest.TestCase):
    def test_no_candidate_readiness_requires_explicit_install_target(self):
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_kit import build_smoke_kit
        from src.evidence.smoke_readiness import build_smoke_readiness

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            build_smoke_kit(root / "out" / "proof" / "tmuf_calibration_smoke_kit")
            write_skin_dir_report(root / "out" / "proof" / "tmuf_skin_dirs.json", roots=[root / "missing"])

            readiness = build_smoke_readiness(root)

            self.assertEqual(readiness["status"], "needs_explicit_stadiumcar_dir")
            self.assertTrue(readiness["does_not_prove_tmuf_smoke"])
            self.assertEqual(readiness["smoke_kit"]["freshness_status"], "fresh_not_run")
            self.assertEqual(readiness["skin_dirs"]["candidate_count"], 0)
            self.assertIn("--install-skins-dir", readiness["commands"]["install_explicit"])
            self.assertNotIn("apply", readiness["next_actions"])

    def test_single_candidate_readiness_recommends_guarded_discovered_install(self):
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_kit import build_smoke_kit
        from src.evidence.smoke_readiness import build_smoke_readiness

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_dir = root / "TrackMania" / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)
            build_smoke_kit(root / "out" / "proof" / "tmuf_calibration_smoke_kit")
            write_skin_dir_report(root / "out" / "proof" / "tmuf_skin_dirs.json", roots=[root])

            readiness = build_smoke_readiness(root)

            self.assertEqual(readiness["status"], "ready_for_guarded_discovered_install")
            self.assertEqual(readiness["skin_dirs"]["candidate_count"], 1)
            self.assertEqual(readiness["selected_candidate"]["path"], install_dir.as_posix())
            self.assertIn("--install-discovered", readiness["commands"]["install_discovered"])
            self.assertIn(str(root), readiness["commands"]["install_discovered"])

    def test_valid_install_receipt_readiness_points_to_smoke_recording(self):
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_kit import build_smoke_kit, install_calibration_skin, write_install_receipt
        from src.evidence.smoke_readiness import build_smoke_readiness

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit_dir = root / "out" / "proof" / "tmuf_calibration_smoke_kit"
            install_dir = root / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)
            build_smoke_kit(kit_dir)
            write_skin_dir_report(root / "out" / "proof" / "tmuf_skin_dirs.json", roots=[root])
            write_install_receipt(install_calibration_skin(install_dir), kit_dir)

            readiness = build_smoke_readiness(root)

            self.assertEqual(readiness["status"], "ready_to_run_tmuf_smoke")
            self.assertTrue(readiness["install_receipt"]["valid"])
            self.assertEqual(readiness["install_receipt"]["path"], str(kit_dir / "proof" / "calibration_install_receipt.json"))
            self.assertIn("--install-receipt", readiness["commands"]["record_smoke"])
            self.assertIn("run_tmuf_calibration_smoke_test", readiness["next_actions"])
            self.assertIn("record_tmuf_smoke_evidence", readiness["next_actions"])

    def test_cli_can_write_readiness_json(self):
        from recipes.smoke_readiness import main
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_kit import build_smoke_kit

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_path = root / "readiness.json"
            build_smoke_kit(root / "out" / "proof" / "tmuf_calibration_smoke_kit")
            write_skin_dir_report(root / "out" / "proof" / "tmuf_skin_dirs.json", roots=[root / "missing"])

            output = main(["--root", str(root), "--write", str(out_path), "--json"])
            data = json.loads(output)

            self.assertEqual(data["status"], "needs_explicit_stadiumcar_dir")
            self.assertTrue(out_path.exists())
            self.assertEqual(json.loads(out_path.read_text())["status"], data["status"])


if __name__ == "__main__":
    unittest.main()
