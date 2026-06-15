import json
import unittest


class ProfileGateTests(unittest.TestCase):
    def test_custom_profiles_are_locked_until_stock_smoke_passes(self):
        from src.profiles.gates import evaluate_profile_gates

        result = evaluate_profile_gates()

        self.assertEqual(result["overall_status"], "custom_profiles_locked")
        self.assertEqual(result["stock_calibration_gate"], "pending_tmuf_smoke")

        fullcar = result["profiles"]["ch2026_fullcar"]
        self.assertEqual(fullcar["status"], "locked")
        self.assertIn("stock_calibration_tmuf_smoke_pending", fullcar["reasons"])
        self.assertEqual(
            fullcar["inputs"]["experimental/base_car/CH_2026_NOT_STOCK_STADIUM_DETAILS_CUSTOM_MESH.zip"][
                "evidence_label"
            ],
            "experimental",
        )
        self.assertIn("Details.dds", fullcar["allowed_outputs_after_unlock"])
        self.assertIn("GBX files", fullcar["allowed_outputs_after_unlock"])

        nomud = result["profiles"]["ch2026_nomud"]
        self.assertEqual(nomud["status"], "locked")
        self.assertIn("ch2026_fullcar_not_proven", nomud["reasons"])
        self.assertIn("nomud_tmuf_smoke_missing", nomud["reasons"])
        self.assertEqual(
            nomud["inputs"]["experimental/flows/remove_guards/bin/Release/net9.0/remove_guards.dll"][
                "evidence_label"
            ],
            "experimental",
        )

    def test_fullcar_can_only_be_ready_after_stock_smoke_passes(self):
        from src.profiles.gates import evaluate_profile_gates

        result = evaluate_profile_gates(stock_calibration_passed=True)

        self.assertEqual(result["stock_calibration_gate"], "passed")
        self.assertEqual(result["profiles"]["ch2026_fullcar"]["status"], "ready_for_experimental_build")
        self.assertEqual(result["profiles"]["ch2026_nomud"]["status"], "locked")
        self.assertIn("ch2026_fullcar_not_proven", result["profiles"]["ch2026_nomud"]["reasons"])

    def test_nomud_can_only_be_ready_after_fullcar_smoke_passes(self):
        from src.profiles.gates import evaluate_profile_gates

        result = evaluate_profile_gates(stock_calibration_passed=True, ch2026_fullcar_passed=True)

        self.assertEqual(result["profiles"]["ch2026_fullcar"]["status"], "proven")
        self.assertEqual(result["profiles"]["ch2026_nomud"]["status"], "ready_for_experimental_build")
        self.assertIn("remove_guards_high_mesh_removes_6_low_mesh_removes_0", result["profiles"]["ch2026_nomud"]["known_evidence"])

    def test_cli_outputs_profile_gate_summary(self):
        from recipes.validate_profile_gates import main

        output = main(["--json"])
        data = json.loads(output)

        self.assertEqual(data["overall_status"], "custom_profiles_locked")
        self.assertEqual(data["profiles"]["ch2026_fullcar"]["status"], "locked")


if __name__ == "__main__":
    unittest.main()
