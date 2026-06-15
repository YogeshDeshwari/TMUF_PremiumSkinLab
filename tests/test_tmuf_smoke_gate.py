import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, ImageDraw


REQUIRED_SCREENSHOT_ROLES = ("front", "side", "rear", "top")


def _write_nonblank_png(path: Path) -> None:
    image = Image.new("RGB", (64, 48), (10, 12, 14))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 56, 40), fill=(220, 20, 180))
    image.save(path)


def _write_role_screenshots(base: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for role in REQUIRED_SCREENSHOT_ROLES:
        path = base / f"tmuf_calibration_{role}.png"
        _write_nonblank_png(path)
        paths[role] = path
    return paths


class TmufSmokeGateTests(unittest.TestCase):
    def test_template_is_not_a_pass_and_lists_required_observations(self):
        from src.evidence.smoke_gate import (
            REQUIRED_OBSERVATIONS,
            REQUIRED_SCREENSHOT_ROLES,
            evaluate_smoke_report,
            write_template,
        )

        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "calibration_tmuf_smoke_template.json"
            write_template(template_path)

            data = json.loads(template_path.read_text())
            self.assertEqual(data["status"], "not_run")
            self.assertEqual(data["artifact"], "out/skins/calibration_stock_diffuse.zip")
            self.assertEqual(set(data["observations"]), set(REQUIRED_OBSERVATIONS))
            self.assertEqual(set(data["screenshot_roles"]), set(REQUIRED_SCREENSHOT_ROLES))
            self.assertTrue(all(value is False for value in data["observations"].values()))

            result = evaluate_smoke_report(template_path, base_dir=Path(tmp))
            self.assertFalse(result["passed"])
            self.assertEqual(result["gbuffer_mapping_status"], "experimental_until_tmuf_smoke")
            self.assertEqual(set(result["missing_observations"]), set(REQUIRED_OBSERVATIONS))
            self.assertEqual(set(result["missing_screenshot_roles"]), set(REQUIRED_SCREENSHOT_ROLES))

    def test_valid_manual_evidence_can_promote_generated_reports(self):
        from src.evidence.smoke_gate import (
            REQUIRED_OBSERVATIONS,
            apply_smoke_result,
            evaluate_smoke_report,
            fingerprint_screenshot_file,
        )

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
            screenshot_roles = {role: path.name for role, path in role_paths.items()}
            screenshots = [screenshot_roles[role] for role in REQUIRED_SCREENSHOT_ROLES]
            smoke_report = base / "calibration_tmuf_smoke.json"
            smoke_report.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "artifact": "out/skins/calibration_stock_diffuse.zip",
                        "status": "passed",
                        "tester": "manual tester",
                        "tmuf_build": "TMUF local install",
                        "test_date_local": "2026-06-15",
                        "screenshots": screenshots,
                        "screenshot_roles": screenshot_roles,
                        "screenshot_evidence": {
                            path.name: fingerprint_screenshot_file(path) for path in role_paths.values()
                        },
                        "observations": {name: True for name in REQUIRED_OBSERVATIONS},
                    }
                )
            )
            generated_report = base / "black_magenta_cyan_blade.json"
            generated_report.write_text(
                json.dumps(
                    {
                        "skin_name": "black_magenta_cyan_blade",
                        "route": "stock_diffuse_only",
                        "package_files": ["Diffuse.dds", "Icon.dds"],
                        "tmuf_smoke_test": "not_run",
                        "proof_gate": {"calibration_stock_diffuse": "required_before_proven_use"},
                        "evidence_status": {"gbuffer_mapping": "experimental_until_tmuf_smoke"},
                        "masks_used": ["mudguards", "center_spine"],
                        "mask_evidence": {
                            "mudguards": {
                                "evidence_status": "proven_local_psd_parts_label_map",
                                "pixel_count": 425340,
                            },
                            "center_spine": {
                                "evidence_status": "experimental_until_tmuf_smoke",
                                "pixel_count": 531368,
                            },
                            "mid_deck_generated_panels": {
                                "evidence_status": "mixed_generated_labels_and_experimental_gbuffer",
                                "pixel_count": 723443,
                            },
                            "front_mudguard_caps": {
                                "evidence_status": "mixed_local_label_and_experimental_gbuffer",
                                "pixel_count": 192838,
                            },
                        },
                    }
                )
            )

            result = evaluate_smoke_report(smoke_report, base_dir=base)
            self.assertTrue(result["passed"])
            self.assertEqual(result["gbuffer_mapping_status"], "proven_by_tmuf_smoke")

            updated = apply_smoke_result(smoke_report, report_paths=[generated_report], base_dir=base)
            self.assertEqual(updated, [generated_report])
            promoted = json.loads(generated_report.read_text())
            self.assertEqual(promoted["tmuf_smoke_test"], "passed")
            self.assertEqual(promoted["evidence_status"]["gbuffer_mapping"], "proven_by_tmuf_smoke")
            self.assertEqual(promoted["proof_gate"]["calibration_stock_diffuse"], "passed")
            self.assertEqual(
                promoted["mask_evidence"]["mudguards"]["evidence_status"],
                "proven_local_psd_parts_label_map",
            )
            self.assertEqual(
                promoted["mask_evidence"]["center_spine"]["evidence_status"],
                "proven_by_tmuf_smoke",
            )
            self.assertEqual(
                promoted["mask_evidence"]["mid_deck_generated_panels"]["evidence_status"],
                "proven_by_tmuf_smoke",
            )
            self.assertEqual(
                promoted["mask_evidence"]["front_mudguard_caps"]["evidence_status"],
                "proven_by_tmuf_smoke",
            )
            self.assertEqual(promoted["tmuf_smoke_evidence"]["screenshots"], screenshots)
            self.assertEqual(promoted["tmuf_smoke_evidence"]["screenshot_roles"], screenshot_roles)
            self.assertIn(screenshot_roles["front"], promoted["tmuf_smoke_evidence"]["screenshot_evidence"])

    def test_apply_skips_non_skin_reports_and_updates_batch_index(self):
        from src.evidence.smoke_gate import (
            REQUIRED_OBSERVATIONS,
            apply_smoke_result,
            fingerprint_screenshot_file,
        )

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
            screenshot_roles = {role: path.name for role, path in role_paths.items()}
            screenshots = [screenshot_roles[role] for role in REQUIRED_SCREENSHOT_ROLES]
            smoke_report = base / "calibration_tmuf_smoke.json"
            smoke_report.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "artifact": "out/skins/calibration_stock_diffuse.zip",
                        "status": "passed",
                        "tester": "manual tester",
                        "tmuf_build": "TMUF local install",
                        "test_date_local": "2026-06-15",
                        "screenshots": screenshots,
                        "screenshot_roles": screenshot_roles,
                        "screenshot_evidence": {
                            path.name: fingerprint_screenshot_file(path) for path in role_paths.values()
                        },
                        "observations": {name: True for name in REQUIRED_OBSERVATIONS},
                    }
                )
            )
            skin_report = base / "black_magenta_cyan_blade.json"
            skin_report.write_text(
                json.dumps(
                    {
                        "skin_name": "black_magenta_cyan_blade",
                        "route": "stock_diffuse_only",
                        "package_files": ["Diffuse.dds", "Icon.dds"],
                        "tmuf_smoke_test": "not_run",
                        "proof_gate": {"calibration_stock_diffuse": "required_before_proven_use"},
                        "evidence_status": {"gbuffer_mapping": "experimental_until_tmuf_smoke"},
                        "mask_evidence": {
                            "center_spine": {
                                "evidence_status": "experimental_until_tmuf_smoke",
                                "pixel_count": 531368,
                            }
                        },
                    }
                )
            )
            batch_index = base / "premium_batch_index.json"
            batch_index.write_text(
                json.dumps(
                    {
                        "schema": "tmuf_premium_skin_lab.premium_batch_index.v1",
                        "route": "stock_diffuse_only",
                        "candidate_count": 1,
                        "does_not_prove_tmuf_smoke": True,
                        "tmuf_smoke_status": "pending",
                        "gbuffer_mapping": "experimental_until_tmuf_smoke",
                        "completion_status": "not_complete_tmuf_smoke_pending",
                        "candidates": [
                            {
                                "skin_name": "black_magenta_cyan_blade",
                                "tmuf_smoke_test": "not_run",
                                "gbuffer_mapping": "experimental_until_tmuf_smoke",
                                "package_files": ["Diffuse.dds", "Icon.dds"],
                            }
                        ],
                    }
                )
            )
            inventory = base / "stock_part_inventory.json"
            inventory_data = {
                "schema": "tmuf_premium_skin_lab.stock_part_inventory.v1",
                "evidence_status": {"tmuf_runtime_visibility": "not_proven_until_smoke"},
            }
            inventory.write_text(json.dumps(inventory_data))

            updated = apply_smoke_result(
                smoke_report,
                report_paths=[skin_report, batch_index, inventory],
                base_dir=base,
            )

            self.assertEqual(updated, [skin_report, batch_index])
            self.assertEqual(json.loads(inventory.read_text()), inventory_data)

            promoted_skin = json.loads(skin_report.read_text())
            self.assertEqual(promoted_skin["tmuf_smoke_test"], "passed")
            self.assertEqual(promoted_skin["evidence_status"]["gbuffer_mapping"], "proven_by_tmuf_smoke")

            promoted_index = json.loads(batch_index.read_text())
            self.assertFalse(promoted_index["does_not_prove_tmuf_smoke"])
            self.assertEqual(promoted_index["tmuf_smoke_status"], "passed")
            self.assertEqual(promoted_index["gbuffer_mapping"], "proven_by_tmuf_smoke")
            self.assertEqual(promoted_index["completion_status"], "stock_calibration_smoke_passed")
            self.assertEqual(promoted_index["candidates"][0]["tmuf_smoke_test"], "passed")
            self.assertEqual(promoted_index["candidates"][0]["gbuffer_mapping"], "proven_by_tmuf_smoke")
            self.assertIn("tmuf_smoke_evidence", promoted_index)

    def test_missing_or_changed_screenshot_fingerprint_prevents_promotion(self):
        from src.evidence.smoke_gate import (
            REQUIRED_OBSERVATIONS,
            apply_smoke_result,
            evaluate_smoke_report,
            fingerprint_screenshot_file,
        )

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
            screenshot_roles = {role: path.name for role, path in role_paths.items()}
            screenshots = [screenshot_roles[role] for role in REQUIRED_SCREENSHOT_ROLES]
            smoke_report = base / "calibration_tmuf_smoke.json"
            report_data = {
                "schema_version": 1,
                "artifact": "out/skins/calibration_stock_diffuse.zip",
                "status": "passed",
                "tester": "manual tester",
                "tmuf_build": "TMUF local install",
                "test_date_local": "2026-06-15",
                "screenshots": screenshots,
                "screenshot_roles": screenshot_roles,
                "observations": {name: True for name in REQUIRED_OBSERVATIONS},
            }
            smoke_report.write_text(json.dumps(report_data))

            missing = evaluate_smoke_report(smoke_report, base_dir=base)
            self.assertFalse(missing["passed"])
            self.assertEqual(set(missing["missing_screenshot_fingerprints"]), set(screenshots))

            report_data["screenshot_evidence"] = {
                path.name: fingerprint_screenshot_file(path) for path in role_paths.values()
            }
            smoke_report.write_text(json.dumps(report_data))
            with Image.open(role_paths["front"]) as image:
                changed_image = image.convert("RGB")
            ImageDraw.Draw(changed_image).point((0, 0), fill=(255, 255, 255))
            changed_image.save(role_paths["front"])

            changed = evaluate_smoke_report(smoke_report, base_dir=base)
            self.assertFalse(changed["passed"])
            self.assertEqual(changed["mismatched_screenshot_fingerprints"], [screenshot_roles["front"]])
            with self.assertRaises(ValueError):
                apply_smoke_result(smoke_report, report_paths=[], base_dir=base)

    def test_invalid_or_blank_screenshot_prevents_promotion(self):
        from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS, apply_smoke_result, evaluate_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            invalid = base / "not_an_image.png"
            invalid.write_bytes(b"not image bytes")
            blank = base / "blank.png"
            Image.new("RGB", (64, 48), (12, 12, 12)).save(blank)
            role_paths = _write_role_screenshots(base)
            role_paths["front"] = invalid
            role_paths["side"] = blank
            screenshot_roles = {role: path.name for role, path in role_paths.items()}
            smoke_report = base / "calibration_tmuf_smoke.json"
            smoke_report.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "artifact": "out/skins/calibration_stock_diffuse.zip",
                        "status": "passed",
                        "tester": "manual tester",
                        "tmuf_build": "TMUF local install",
                        "test_date_local": "2026-06-15",
                        "screenshots": [screenshot_roles[role] for role in REQUIRED_SCREENSHOT_ROLES],
                        "screenshot_roles": screenshot_roles,
                        "observations": {name: True for name in REQUIRED_OBSERVATIONS},
                    }
                )
            )

            result = evaluate_smoke_report(smoke_report, base_dir=base)
            self.assertFalse(result["passed"])
            self.assertEqual(result["invalid_screenshots"], [invalid.name])
            self.assertEqual(result["blank_screenshots"], [blank.name])
            with self.assertRaises(ValueError):
                apply_smoke_result(smoke_report, report_paths=[], base_dir=base)

    def test_missing_screenshot_prevents_promotion(self):
        from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS, apply_smoke_result, evaluate_smoke_report

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            role_paths = _write_role_screenshots(base)
            role_paths["front"] = base / "missing.png"
            screenshot_roles = {role: path.name for role, path in role_paths.items()}
            smoke_report = base / "calibration_tmuf_smoke.json"
            smoke_report.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "artifact": "out/skins/calibration_stock_diffuse.zip",
                        "status": "passed",
                        "tester": "manual tester",
                        "tmuf_build": "TMUF local install",
                        "test_date_local": "2026-06-15",
                        "screenshots": [screenshot_roles[role] for role in REQUIRED_SCREENSHOT_ROLES],
                        "screenshot_roles": screenshot_roles,
                        "observations": {name: True for name in REQUIRED_OBSERVATIONS},
                    }
                )
            )

            result = evaluate_smoke_report(smoke_report, base_dir=base)
            self.assertFalse(result["passed"])
            self.assertEqual(result["missing_screenshots"], ["missing.png"])
            with self.assertRaises(ValueError):
                apply_smoke_result(smoke_report, report_paths=[], base_dir=base)


if __name__ == "__main__":
    unittest.main()
