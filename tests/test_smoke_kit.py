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
            self.assertEqual(
                manifest["supplemental_panel_probe_skin"],
                "skins/calibration_panel_family_probe.zip",
            )
            self.assertEqual(manifest["smoke_run_manifest"], "proof/tmuf_smoke_run_manifest.json")
            self.assertIn("proof/calibration_tmuf_smoke_template.json", manifest["files"])
            self.assertIn("proof/tmuf_smoke_run_manifest.json", manifest["files"])
            self.assertIn("skins/calibration_panel_family_probe.zip", manifest["files"])
            self.assertIn("reports/calibration_panel_family_probe.json", manifest["files"])
            self.assertIn("previews/calibration_panel_family_probe_projected_side_top_rear.png", manifest["files"])
            self.assertIn("previews/calibration_stock_diffuse_projected_side_top_rear.png", manifest["files"])
            self.assertIn("previews/tmuf_smoke_contact_sheet.png", manifest["files"])
            self.assertTrue(any("recipes/record_tmuf_smoke.py" in step for step in manifest["next_steps"]))
            self.assertTrue(
                any("calibration_panel_family_probe.zip" in step for step in manifest["next_steps"])
            )

            run_manifest_path = manifest_path.parent / "proof" / "tmuf_smoke_run_manifest.json"
            self.assertTrue(run_manifest_path.exists())
            run_manifest = json.loads(run_manifest_path.read_text())
            self.assertEqual(run_manifest["schema"], "tmuf_premium_skin_lab.tmuf_smoke_run_manifest.v1")
            self.assertEqual(run_manifest["status"], "not_run")
            self.assertTrue(run_manifest["does_not_prove_tmuf_smoke"])
            self.assertEqual(run_manifest["route"], "stock_diffuse_only")
            self.assertEqual(
                run_manifest["supplemental_artifacts"]["panel_family_probe"]["kit_skin"],
                "skins/calibration_panel_family_probe.zip",
            )
            self.assertTrue(
                run_manifest["supplemental_artifacts"]["panel_family_probe"]["does_not_prove_tmuf_smoke"]
            )
            self.assertEqual(run_manifest["required_screenshot_roles"], ["front", "side", "rear", "top"])
            self.assertIn("nose_is_red", run_manifest["required_observations"])
            self.assertIn("package_loads_without_custom_gbx", run_manifest["required_observations"])
            record_command = " ".join(run_manifest["commands"]["record_explicit_observations"])
            self.assertIn("--install-receipt", record_command)
            self.assertIn("--screenshot-role front=", record_command)
            self.assertIn("--screenshot-role side=", record_command)
            self.assertIn("--screenshot-role rear=", record_command)
            self.assertIn("--screenshot-role top=", record_command)
            self.assertIn("--confirm-observation nose_is_red", record_command)
            self.assertEqual(run_manifest["install_discovery"]["does_not_prove_tmuf_smoke"], True)

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

            (kit_dir / "proof" / "tmuf_smoke_run_manifest.json").write_text("{}\n")

            stale_manifest = validate_smoke_kit(kit_dir)
            self.assertFalse(stale_manifest["fresh"])
            self.assertIn("proof/tmuf_smoke_run_manifest.json", stale_manifest["stale_files"])

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

    def test_install_calibration_skin_can_optionally_copy_panel_probe_with_receipt(self):
        from src.evidence.smoke_kit import (
            PANEL_PROBE_NAME,
            PANEL_PROBE_SKIN,
            install_calibration_skin,
            write_install_receipt,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_dir = root / "Skins" / "Vehicles" / "StadiumCar"
            kit_dir = root / "kit"
            install_dir.mkdir(parents=True)

            result = install_calibration_skin(install_dir, include_panel_probe=True)

            copied_probe = install_dir / f"{PANEL_PROBE_NAME}.zip"
            self.assertTrue(copied_probe.exists())
            self.assertEqual(copied_probe.read_bytes(), PANEL_PROBE_SKIN.read_bytes())
            self.assertEqual(
                sorted(path.name for path in install_dir.iterdir()),
                ["calibration_panel_family_probe.zip", "calibration_stock_diffuse.zip"],
            )

            supplemental = result["installed_supplemental_skins"]
            self.assertEqual(len(supplemental), 1)
            self.assertEqual(supplemental[0]["name"], PANEL_PROBE_NAME)
            self.assertEqual(supplemental[0]["installed_skin"], str(copied_probe))
            self.assertTrue(supplemental[0]["does_not_prove_tmuf_smoke"])
            self.assertEqual(supplemental[0]["sha256"], supplemental[0]["source_sha256"])

            receipt_path = write_install_receipt(result, kit_dir)
            receipt = json.loads(receipt_path.read_text())
            self.assertTrue(receipt["does_not_prove_tmuf_smoke"])
            self.assertEqual(receipt["installed_skin"], str(install_dir / "calibration_stock_diffuse.zip"))
            self.assertEqual(receipt["installed_supplemental_skins"], supplemental)
            self.assertIn("inspect_panel_family_probe_in_tmuf", receipt["next_required_evidence"])

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

    def test_cli_install_writes_local_receipt_without_touching_skin_folder_extra_files(self):
        from recipes.prepare_tmuf_smoke_kit import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit_dir = root / "kit"
            install_dir = root / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)

            output = main(
                [
                    "--out-dir",
                    str(kit_dir),
                    "--install-skins-dir",
                    str(install_dir),
                    "--json",
                ]
            )
            data = json.loads(output)

            receipt_path = Path(data["install_receipt"])
            self.assertEqual(receipt_path, kit_dir / "proof" / "calibration_install_receipt.json")
            self.assertTrue(receipt_path.exists())
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual(receipt["schema"], "tmuf_premium_skin_lab.calibration_install_receipt.v1")
            self.assertEqual(receipt["status"], "installed_not_tested")
            self.assertEqual(receipt["route"], "skins_vehicles_stadiumcar")
            self.assertTrue(receipt["does_not_prove_tmuf_smoke"])
            self.assertEqual(receipt["installed_skin"], str(install_dir / "calibration_stock_diffuse.zip"))
            self.assertEqual(receipt["sha256"], data["install"]["sha256"])
            self.assertIn("run_tmuf_calibration_smoke_test", receipt["next_required_evidence"])
            self.assertEqual(sorted(path.name for path in install_dir.iterdir()), ["calibration_stock_diffuse.zip"])

    def test_cli_install_can_create_explicit_recognized_target_when_requested(self):
        from recipes.prepare_tmuf_smoke_kit import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit_dir = root / "kit"
            install_dir = root / "GameData" / "Skins" / "Vehicles" / "StadiumCar"

            output = main(
                [
                    "--out-dir",
                    str(kit_dir),
                    "--install-skins-dir",
                    str(install_dir),
                    "--create-install-target",
                    "--json",
                ]
            )
            data = json.loads(output)

            self.assertTrue(install_dir.is_dir())
            self.assertTrue((install_dir / "calibration_stock_diffuse.zip").exists())
            self.assertEqual(data["install"]["route"], "gamedata_skins_vehicles_stadiumcar")
            self.assertEqual(data["install"]["selection_mode"], "explicit_install_target_created")
            self.assertTrue(data["install"]["install_target_setup"]["created"])
            self.assertTrue(data["install"]["install_target_setup"]["does_not_prove_tmuf_smoke"])

            receipt = json.loads(Path(data["install_receipt"]).read_text())
            self.assertEqual(receipt["selection_mode"], "explicit_install_target_created")
            self.assertTrue(receipt["install_target_setup"]["created"])
            self.assertTrue(receipt["install_target_setup"]["does_not_prove_tmuf_smoke"])

    def test_cli_install_can_include_panel_probe_when_explicitly_requested(self):
        from recipes.prepare_tmuf_smoke_kit import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit_dir = root / "kit"
            install_dir = root / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)

            output = main(
                [
                    "--out-dir",
                    str(kit_dir),
                    "--install-skins-dir",
                    str(install_dir),
                    "--install-panel-probe",
                    "--json",
                ]
            )
            data = json.loads(output)

            self.assertEqual(
                sorted(path.name for path in install_dir.iterdir()),
                ["calibration_panel_family_probe.zip", "calibration_stock_diffuse.zip"],
            )
            supplemental = data["install"]["installed_supplemental_skins"]
            self.assertEqual(supplemental[0]["name"], "calibration_panel_family_probe")
            self.assertTrue(supplemental[0]["does_not_prove_tmuf_smoke"])

            receipt = json.loads(Path(data["install_receipt"]).read_text())
            self.assertEqual(receipt["installed_supplemental_skins"], supplemental)

    def test_cli_install_discovered_single_candidate_writes_receipt_and_discovery_audit(self):
        from recipes.prepare_tmuf_smoke_kit import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit_dir = root / "kit"
            install_dir = root / "TrackMania" / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)

            output = main(
                [
                    "--out-dir",
                    str(kit_dir),
                    "--install-discovered",
                    "--search-root",
                    str(root),
                    "--json",
                ]
            )
            data = json.loads(output)

            copied = install_dir / "calibration_stock_diffuse.zip"
            self.assertTrue(copied.exists())
            self.assertEqual(data["install"]["selection_mode"], "single_discovered_candidate")
            self.assertEqual(data["install"]["selected_candidate"]["path"], install_dir.as_posix())
            self.assertEqual(data["install"]["discovery"]["candidate_count"], 1)

            receipt = json.loads(Path(data["install_receipt"]).read_text())
            self.assertEqual(receipt["selection_mode"], "single_discovered_candidate")
            self.assertEqual(receipt["selected_candidate"]["path"], install_dir.as_posix())
            self.assertEqual(receipt["discovery"]["candidate_count"], 1)

            run_manifest = json.loads((kit_dir / "proof" / "tmuf_smoke_run_manifest.json").read_text())
            self.assertEqual(run_manifest["install_discovery"]["candidate_count"], 1)

    def test_cli_install_discovered_refuses_zero_or_multiple_candidates(self):
        from recipes.prepare_tmuf_smoke_kit import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError) as missing_context:
                main(
                    [
                        "--out-dir",
                        str(root / "missing_kit"),
                        "--install-discovered",
                        "--search-root",
                        str(root),
                    ]
                )
            self.assertIn("exactly one", str(missing_context.exception))
            self.assertIn("found 0", str(missing_context.exception))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "one" / "Skins" / "Vehicles" / "StadiumCar").mkdir(parents=True)
            (root / "two" / "Skins" / "Vehicles" / "StadiumCar").mkdir(parents=True)

            with self.assertRaises(ValueError) as multiple_context:
                main(
                    [
                        "--out-dir",
                        str(root / "ambiguous_kit"),
                        "--install-discovered",
                        "--search-root",
                        str(root),
                    ]
                )
            self.assertIn("exactly one", str(multiple_context.exception))
            self.assertIn("found 2", str(multiple_context.exception))


if __name__ == "__main__":
    unittest.main()
