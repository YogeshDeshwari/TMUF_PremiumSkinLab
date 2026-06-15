import json
from pathlib import Path
import tempfile
import unittest


class PremiumVisualReviewSessionTests(unittest.TestCase):
    def test_session_creates_capture_slots_and_commands_for_all_candidates_without_fake_screenshots(self):
        from src.evidence.premium_visual_review import REQUIRED_PREMIUM_REVIEW_ROLES
        from src.evidence.premium_visual_review_session import build_premium_visual_review_session
        from src.stock_diffuse.premium import CANDIDATE_NAMES

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            session_dir = root / "out" / "proof" / "premium_visual_review_session"

            manifest = build_premium_visual_review_session(session_dir, base_dir=root)

            self.assertEqual(manifest["schema"], "tmuf_premium_skin_lab.premium_visual_review_session.v1")
            self.assertEqual(manifest["status"], "awaiting_tmuf_premium_screenshots")
            self.assertEqual(manifest["candidate_count"], len(CANDIDATE_NAMES))
            self.assertTrue(manifest["does_not_prove_tmuf_smoke"])
            self.assertTrue(manifest["does_not_prove_gbuffer_mapping"])
            self.assertEqual([item["skin_name"] for item in manifest["candidates"]], CANDIDATE_NAMES)

            first = manifest["candidates"][0]
            self.assertEqual(first["skin_name"], "black_magenta_cyan_blade")
            self.assertEqual(first["default_verdict"], "needs_iteration")
            self.assertEqual([slot["role"] for slot in first["screenshot_slots"]], REQUIRED_PREMIUM_REVIEW_ROLES)
            for slot in first["screenshot_slots"]:
                self.assertTrue(slot["path"].endswith(f"black_magenta_cyan_blade/{slot['role']}.png"))
                self.assertFalse(slot["exists"])
                self.assertFalse(Path(slot["path"]).exists())

            self.assertIn("recipes/record_premium_visual_review.py", first["record_command"])
            self.assertIn("--skin-name black_magenta_cyan_blade", first["record_command"])
            self.assertIn("--verdict needs_iteration", first["record_command"])
            self.assertIn("--output", first["record_command"])
            self.assertTrue((session_dir / "session_manifest.json").exists())
            self.assertTrue((session_dir / "record_premium_visual_review_commands.txt").exists())
            self.assertTrue((session_dir / "README_premium_visual_review_session.md").exists())
            self.assertEqual(
                json.loads((session_dir / "session_manifest.json").read_text())["candidate_count"],
                len(CANDIDATE_NAMES),
            )

    def test_session_cli_can_prepare_subset_for_one_candidate(self):
        from recipes.prepare_premium_visual_review_session import main

        with tempfile.TemporaryDirectory() as tmp:
            session_dir = Path(tmp) / "session"
            output = main(
                [
                    "--session-dir",
                    str(session_dir),
                    "--candidate",
                    "black_cyan_spine",
                    "--json",
                ]
            )
            data = json.loads(output)

            self.assertEqual(data["status"], "awaiting_tmuf_premium_screenshots")
            self.assertEqual(data["candidate_count"], 1)
            self.assertEqual(data["candidates"][0]["skin_name"], "black_cyan_spine")
            self.assertTrue((session_dir / "session_manifest.json").exists())
            self.assertTrue((session_dir / "record_premium_visual_review_commands.txt").exists())


if __name__ == "__main__":
    unittest.main()
