import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw


REQUIRED_SCREENSHOT_ROLES = ("front", "side", "rear", "top")


def _write_nonblank_png(path: Path) -> None:
    image = Image.new("RGB", (64, 48), (9, 10, 12))
    draw = ImageDraw.Draw(image)
    draw.rectangle((6, 6, 58, 42), fill=(0, 210, 240))
    image.save(path)


def _write_role_screenshots(base: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for role in REQUIRED_SCREENSHOT_ROLES:
        path = base / f"tmuf_{role}.png"
        _write_nonblank_png(path)
        paths[role] = path
    return paths


class SmokeRecordTests(unittest.TestCase):
    def test_record_copies_screenshots_and_writes_passable_report(self):
        from src.evidence.smoke_gate import evaluate_smoke_report
        from src.evidence.smoke_record import record_calibration_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"

            written = record_calibration_smoke_report(
                output_path=output,
                tester="manual tester",
                tmuf_build="TMUF local install",
                test_date_local="2026-06-15",
                screenshot_roles=role_paths,
                all_required_observations_passed=True,
                notes="Calibration colors matched in car selection preview.",
                base_dir=base,
            )

            self.assertEqual(written, output)
            data = json.loads(output.read_text())
            self.assertEqual(data["status"], "passed")
            self.assertEqual(data["route"], "stock_diffuse_only")
            self.assertTrue(all(data["observations"].values()))
            self.assertEqual(set(data["screenshot_roles"]), set(REQUIRED_SCREENSHOT_ROLES))
            self.assertEqual(len(data["screenshots"]), 4)
            front_path = data["screenshot_roles"]["front"]
            self.assertTrue((base / front_path).exists())
            fingerprint = data["screenshot_evidence"][front_path]
            self.assertEqual(fingerprint["width"], 64)
            self.assertEqual(fingerprint["height"], 48)
            self.assertEqual(fingerprint["size_bytes"], (base / front_path).stat().st_size)
            self.assertRegex(fingerprint["sha256"], r"^[0-9a-f]{64}$")

            result = evaluate_smoke_report(output, base_dir=base)
            self.assertTrue(result["passed"])
            self.assertEqual(result["gbuffer_mapping_status"], "proven_by_tmuf_smoke")
            self.assertEqual(result["missing_screenshot_roles"], [])

    def test_recorded_report_fails_if_copied_screenshot_changes(self):
        from src.evidence.smoke_gate import evaluate_smoke_report
        from src.evidence.smoke_record import record_calibration_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"

            record_calibration_smoke_report(
                output_path=output,
                tester="manual tester",
                tmuf_build="TMUF local install",
                test_date_local="2026-06-15",
                screenshot_roles=role_paths,
                all_required_observations_passed=True,
                base_dir=base,
            )
            data = json.loads(output.read_text())
            copied = base / data["screenshot_roles"]["front"]
            with Image.open(copied) as image:
                changed_image = image.convert("RGB")
            ImageDraw.Draw(changed_image).point((0, 0), fill=(255, 255, 255))
            changed_image.save(copied)

            result = evaluate_smoke_report(output, base_dir=base)
            self.assertFalse(result["passed"])
            self.assertEqual(result["mismatched_screenshot_fingerprints"], [data["screenshot_roles"]["front"]])

    def test_passed_report_requires_explicit_required_observation_confirmation(self):
        from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS
        from src.evidence.smoke_record import record_calibration_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"

            with self.assertRaises(ValueError) as context:
                record_calibration_smoke_report(
                    output_path=output,
                    tester="manual tester",
                    tmuf_build="TMUF local install",
                    test_date_local="2026-06-15",
                    screenshot_roles=role_paths,
                    all_required_observations_passed=False,
                    base_dir=base,
                )

            self.assertIn("all required observations", str(context.exception))
            self.assertFalse(output.exists())

            with self.assertRaises(ValueError) as missing_context:
                record_calibration_smoke_report(
                    output_path=output,
                    tester="manual tester",
                    tmuf_build="TMUF local install",
                    test_date_local="2026-06-15",
                    screenshot_roles=role_paths,
                    all_required_observations_passed=False,
                    confirmed_observations=REQUIRED_OBSERVATIONS[:-1],
                    base_dir=base,
                )
            self.assertIn(REQUIRED_OBSERVATIONS[-1], str(missing_context.exception))

    def test_record_accepts_each_required_observation_explicitly(self):
        from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS, evaluate_smoke_report
        from src.evidence.smoke_record import record_calibration_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"

            record_calibration_smoke_report(
                output_path=output,
                tester="manual tester",
                tmuf_build="TMUF local install",
                test_date_local="2026-06-15",
                screenshot_roles=role_paths,
                all_required_observations_passed=False,
                confirmed_observations=REQUIRED_OBSERVATIONS,
                base_dir=base,
            )

            data = json.loads(output.read_text())
            self.assertEqual(data["observation_confirmation_mode"], "explicit")
            self.assertTrue(all(data["observations"].values()))
            self.assertTrue(evaluate_smoke_report(output, base_dir=base)["passed"])

    def test_record_rejects_unknown_observation_names(self):
        from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS
        from src.evidence.smoke_record import record_calibration_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"

            with self.assertRaises(ValueError) as context:
                record_calibration_smoke_report(
                    output_path=output,
                    tester="manual tester",
                    tmuf_build="TMUF local install",
                    test_date_local="2026-06-15",
                    screenshot_roles=role_paths,
                    all_required_observations_passed=False,
                    confirmed_observations=[*REQUIRED_OBSERVATIONS, "not_real"],
                    base_dir=base,
                )

            self.assertIn("not_real", str(context.exception))
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
                    screenshot_roles={
                        "front": base / "missing.png",
                        **{role: path for role, path in _write_role_screenshots(base).items() if role != "front"},
                    },
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
                    screenshot_roles={
                        "front": invalid,
                        **{role: path for role, path in _write_role_screenshots(base).items() if role != "front"},
                    },
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
                    screenshot_roles={
                        "front": blank,
                        **{role: path for role, path in _write_role_screenshots(base).items() if role != "front"},
                    },
                    all_required_observations_passed=True,
                    base_dir=base,
                )
            self.assertIn("nonblank", str(blank_context.exception))
            self.assertFalse(output.exists())

    def test_record_requires_all_screenshot_roles(self):
        from src.evidence.smoke_record import record_calibration_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
            output = base / "out" / "proof" / "calibration_tmuf_smoke.json"

            with self.assertRaises(ValueError) as context:
                record_calibration_smoke_report(
                    output_path=output,
                    tester="manual tester",
                    tmuf_build="TMUF local install",
                    test_date_local="2026-06-15",
                    screenshot_roles={role: path for role, path in role_paths.items() if role != "top"},
                    all_required_observations_passed=True,
                    base_dir=base,
                )

            self.assertIn("Missing required screenshot roles", str(context.exception))
            self.assertFalse(output.exists())

    def test_record_recipe_creates_evaluable_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
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
                    *[
                        flag
                        for role, path in role_paths.items()
                        for flag in ("--screenshot-role", f"{role}={path}")
                    ],
                    *[
                        flag
                        for observation in [
                            "nose_is_red",
                            "tail_is_blue",
                            "left_side_is_green",
                            "right_side_is_yellow",
                            "roof_high_surfaces_are_white",
                            "lower_floor_surfaces_are_dark",
                            "mudguards_are_magenta",
                            "centerline_is_cyan",
                            "package_loads_without_custom_gbx",
                        ]
                        for flag in ("--confirm-observation", observation)
                    ],
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn(str(output), result.stdout)
            data = json.loads(output.read_text())
            self.assertEqual(data["status"], "passed")
            self.assertEqual(set(data["screenshot_roles"]), set(REQUIRED_SCREENSHOT_ROLES))


if __name__ == "__main__":
    unittest.main()
