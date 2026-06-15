import json
from pathlib import Path
import tempfile
import unittest


class PremiumReviewInstallTests(unittest.TestCase):
    def test_install_premium_review_skins_copies_all_candidates_without_proof_claim(self):
        from src.evidence.premium_review import install_premium_review_skins, write_premium_review_receipt
        from src.stock_diffuse.premium import CANDIDATE_NAMES

        with tempfile.TemporaryDirectory() as tmp:
            install_dir = Path(tmp) / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)

            result = install_premium_review_skins(install_dir)
            receipt = write_premium_review_receipt(result, Path(tmp) / "premium_review_receipt.json")

            self.assertEqual(result["status"], "installed_for_visual_review_not_tested")
            self.assertEqual(result["route"], "skins_vehicles_stadiumcar")
            self.assertEqual(result["candidate_count"], len(CANDIDATE_NAMES))
            self.assertEqual([item["name"] for item in result["installed_skins"]], CANDIDATE_NAMES)
            self.assertEqual(result["calibration_gate_status"], "pending_tmuf_smoke")
            self.assertTrue(result["does_not_prove_tmuf_smoke"])
            self.assertIn("run_tmuf_calibration_smoke_test", result["next_required_evidence"])

            for item in result["installed_skins"]:
                copied = Path(item["installed_skin"])
                source = Path(item["source_skin"])
                self.assertEqual(copied.parent, install_dir)
                self.assertEqual(copied.name, f"{item['name']}.zip")
                self.assertTrue(copied.exists())
                self.assertEqual(copied.read_bytes(), source.read_bytes())
                self.assertEqual(item["sha256"], item["source_sha256"])
                self.assertEqual(item["package_route"], "stock_diffuse_only")
                self.assertEqual(item["tmuf_smoke_test"], "not_run")
                self.assertTrue(item["does_not_prove_tmuf_smoke"])

            data = json.loads(receipt.read_text())
            self.assertEqual(data["schema"], "tmuf_premium_skin_lab.premium_review_install_receipt.v1")
            self.assertEqual(data["candidate_count"], len(CANDIDATE_NAMES))
            self.assertTrue(data["does_not_prove_tmuf_smoke"])
            self.assertEqual(data["installed_skins"][0]["name"], CANDIDATE_NAMES[0])

    def test_premium_review_cli_installs_to_explicit_target_and_emits_json(self):
        from recipes.install_premium_review_skins import main
        from src.stock_diffuse.premium import CANDIDATE_NAMES

        with tempfile.TemporaryDirectory() as tmp:
            install_dir = Path(tmp) / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)
            receipt = Path(tmp) / "receipt.json"

            output = main([
                "--install-skins-dir",
                str(install_dir),
                "--receipt",
                str(receipt),
                "--json",
            ])
            data = json.loads(output)

            self.assertEqual(data["status"], "installed_for_visual_review_not_tested")
            self.assertEqual(data["candidate_count"], len(CANDIDATE_NAMES))
            self.assertEqual(data["receipt"], str(receipt))
            self.assertTrue(receipt.exists())
            self.assertTrue((install_dir / f"{CANDIDATE_NAMES[-1]}.zip").exists())


if __name__ == "__main__":
    unittest.main()
