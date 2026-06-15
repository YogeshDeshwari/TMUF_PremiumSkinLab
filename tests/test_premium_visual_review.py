import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw


REVIEW_ROLES = ("front", "side", "rear", "top")


def _write_nonblank_png(path: Path) -> None:
    image = Image.new("RGB", (80, 60), (7, 9, 11))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 10, 68, 50), fill=(0, 190, 255))
    image.save(path)


def _write_role_screenshots(base: Path) -> dict[str, Path]:
    screenshots: dict[str, Path] = {}
    for role in REVIEW_ROLES:
        path = base / f"{role}.png"
        _write_nonblank_png(path)
        screenshots[role] = path
    return screenshots


class PremiumVisualReviewTests(unittest.TestCase):
    def test_record_visual_review_copies_fingerprinted_screenshots_without_claiming_mapping_proof(self):
        from src.evidence.premium_visual_review import evaluate_premium_visual_review, record_premium_visual_review

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            output = base / "out" / "proof" / "premium_visual_review.json"
            screenshots = _write_role_screenshots(base)

            path = record_premium_visual_review(
                skin_name="black_magenta_cyan_blade",
                verdict="accepted",
                tester="manual tester",
                tmuf_build="TMUF local install",
                test_date_local="2026-06-15",
                screenshot_roles=screenshots,
                notes="reads clearly in garage",
                output_path=output,
                base_dir=base,
            )

            data = json.loads(path.read_text())
            self.assertEqual(data["schema"], "tmuf_premium_skin_lab.premium_visual_review.v1")
            self.assertEqual(data["skin_name"], "black_magenta_cyan_blade")
            self.assertEqual(data["verdict"], "accepted")
            self.assertEqual(data["status"], "visual_review_recorded")
            self.assertEqual(set(data["screenshot_roles"]), set(REVIEW_ROLES))
            self.assertTrue(data["does_not_prove_tmuf_smoke"])
            self.assertTrue(data["does_not_prove_gbuffer_mapping"])
            self.assertEqual(data["calibration_gate_status"], "pending_or_separate")

            for role, copied in data["screenshot_roles"].items():
                copied_path = base / copied
                self.assertTrue(copied_path.exists())
                self.assertIn(copied, data["screenshot_evidence"])
                self.assertEqual(data["screenshot_evidence"][copied]["width"], 80)
                self.assertEqual(data["screenshot_evidence"][copied]["height"], 60)

            result = evaluate_premium_visual_review(path, base_dir=base)
            self.assertTrue(result["valid"])
            self.assertEqual(result["missing_screenshot_roles"], [])
            self.assertEqual(result["blank_screenshots"], [])
            self.assertEqual(result["mismatched_screenshot_fingerprints"], [])

    def test_record_visual_review_rejects_unknown_skin_or_missing_screenshot_role(self):
        from src.evidence.premium_visual_review import record_premium_visual_review

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            screenshots = _write_role_screenshots(base)

            with self.assertRaisesRegex(ValueError, "Unknown premium candidate"):
                record_premium_visual_review(
                    skin_name="not_a_candidate",
                    verdict="accepted",
                    tester="manual tester",
                    tmuf_build="TMUF local install",
                    test_date_local="2026-06-15",
                    screenshot_roles=screenshots,
                    output_path=base / "review.json",
                    base_dir=base,
                )

            missing_top = {role: path for role, path in screenshots.items() if role != "top"}
            with self.assertRaisesRegex(ValueError, "Missing required screenshot roles"):
                record_premium_visual_review(
                    skin_name="black_magenta_cyan_blade",
                    verdict="accepted",
                    tester="manual tester",
                    tmuf_build="TMUF local install",
                    test_date_local="2026-06-15",
                    screenshot_roles=missing_top,
                    output_path=base / "review.json",
                    base_dir=base,
                )

    def test_premium_visual_review_cli_writes_json_report(self):
        from recipes.record_premium_visual_review import main

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            screenshots = _write_role_screenshots(base)
            output = base / "premium_visual_review.json"

            result = main(
                [
                    "--skin-name",
                    "black_magenta_cyan_blade",
                    "--verdict",
                    "needs_iteration",
                    "--tester",
                    "manual tester",
                    "--tmuf-build",
                    "TMUF local install",
                    "--test-date-local",
                    "2026-06-15",
                    "--output",
                    str(output),
                    "--base-dir",
                    str(base),
                    *[
                        value
                        for role, path in screenshots.items()
                        for value in ("--screenshot-role", f"{role}={path}")
                    ],
                    "--notes",
                    "tail stripe too weak",
                    "--json",
                ]
            )

            data = json.loads(result)
            self.assertEqual(data["status"], "visual_review_recorded")
            self.assertEqual(data["verdict"], "needs_iteration")
            self.assertEqual(data["path"], str(output))
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
