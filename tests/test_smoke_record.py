import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw


def _write_nonblank_png(path: Path) -> None:
    image = Image.new("RGB", (64, 48), (9, 10, 12))
    draw = ImageDraw.Draw(image)
    draw.rectangle((6, 6, 58, 42), fill=(0, 210, 240))
    image.save(path)


class SmokeRecordTests(unittest.TestCase):
    def test_record_copies_screenshots_and_writes_passable_report(self):
        from src.evidence.smoke_gate import evaluate_smoke_report
        from src.evidence.smoke_record import record_calibration_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            screenshot = base / "tmuf_front_left.png"
            _write_nonblank_png(screenshot)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"

            written = record_calibration_smoke_report(
                output_path=output,
                tester="manual tester",
                tmuf_build="TMUF local install",
                test_date_local="2026-06-15",
                screenshot_paths=[screenshot],
                all_required_observations_passed=True,
                notes="Calibration colors matched in car selection preview.",
                base_dir=base,
            )

            self.assertEqual(written, output)
            data = json.loads(output.read_text())
            self.assertEqual(data["status"], "passed")
            self.assertEqual(data["route"], "stock_diffuse_only")
            self.assertTrue(all(data["observations"].values()))
            self.assertEqual(data["screenshots"], ["out/proof/tmuf_smoke_screenshots/tmuf_front_left.png"])
            self.assertTrue((base / data["screenshots"][0]).exists())

            result = evaluate_smoke_report(output, base_dir=base)
            self.assertTrue(result["passed"])
            self.assertEqual(result["gbuffer_mapping_status"], "proven_by_tmuf_smoke")

    def test_passed_report_requires_explicit_required_observation_confirmation(self):
        from src.evidence.smoke_record import record_calibration_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            screenshot = base / "tmuf_front_left.png"
            _write_nonblank_png(screenshot)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"

            with self.assertRaises(ValueError) as context:
                record_calibration_smoke_report(
                    output_path=output,
                    tester="manual tester",
                    tmuf_build="TMUF local install",
                    test_date_local="2026-06-15",
                    screenshot_paths=[screenshot],
                    all_required_observations_passed=False,
                    base_dir=base,
                )

            self.assertIn("all required observations", str(context.exception))
            self.assertFalse(output.exists())

    def test_passed_report_requires_existing_screenshots(self):
        from src.evidence.smoke_record import record_calibration_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"

            with self.assertRaises(FileNotFoundError):
                record_calibration_smoke_report(
                    output_path=output,
                    tester="manual tester",
                    tmuf_build="TMUF local install",
                    test_date_local="2026-06-15",
                    screenshot_paths=[base / "missing.png"],
                    all_required_observations_passed=True,
                    base_dir=base,
                )

            self.assertFalse(output.exists())

    def test_passed_report_requires_readable_nonblank_screenshots(self):
        from src.evidence.smoke_record import record_calibration_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            invalid = base / "not_an_image.png"
            invalid.write_bytes(b"not image bytes")
            blank = base / "blank.png"
            Image.new("RGB", (64, 48), (12, 12, 12)).save(blank)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"

            with self.assertRaises(ValueError) as invalid_context:
                record_calibration_smoke_report(
                    output_path=output,
                    tester="manual tester",
                    tmuf_build="TMUF local install",
                    test_date_local="2026-06-15",
                    screenshot_paths=[invalid],
                    all_required_observations_passed=True,
                    base_dir=base,
                )
            self.assertIn("readable image", str(invalid_context.exception))

            with self.assertRaises(ValueError) as blank_context:
                record_calibration_smoke_report(
                    output_path=output,
                    tester="manual tester",
                    tmuf_build="TMUF local install",
                    test_date_local="2026-06-15",
                    screenshot_paths=[blank],
                    all_required_observations_passed=True,
                    base_dir=base,
                )
            self.assertIn("nonblank", str(blank_context.exception))
            self.assertFalse(output.exists())

    def test_record_recipe_creates_evaluable_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            screenshot = base / "tmuf_front_left.png"
            _write_nonblank_png(screenshot)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"
            recipe = Path(__file__).resolve().parents[1] / "recipes" / "record_tmuf_smoke.py"

            result = subprocess.run(
                [
                    sys.executable,
                    str(recipe),
                    "--output",
                    str(output),
                    "--base-dir",
                    str(base),
                    "--tester",
                    "manual tester",
                    "--tmuf-build",
                    "TMUF local install",
                    "--test-date-local",
                    "2026-06-15",
                    "--screenshot",
                    str(screenshot),
                    "--all-required-observations-passed",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn(str(output), result.stdout)
            data = json.loads(output.read_text())
            self.assertEqual(data["status"], "passed")
            self.assertEqual(data["screenshots"], ["out/proof/tmuf_smoke_screenshots/tmuf_front_left.png"])


if __name__ == "__main__":
    unittest.main()
