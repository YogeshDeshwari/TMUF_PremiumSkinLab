import json
from pathlib import Path
import shlex
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

    def test_explicit_install_target_preflight_recommends_exact_install_command(self):
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_kit import build_smoke_kit
        from src.evidence.smoke_readiness import build_smoke_readiness

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_dir = root / "Manual Prefix" / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)
            build_smoke_kit(root / "out" / "proof" / "tmuf_calibration_smoke_kit")
            write_skin_dir_report(root / "out" / "proof" / "tmuf_skin_dirs.json", roots=[root / "missing"])

            readiness = build_smoke_readiness(root, install_target=install_dir)

            self.assertEqual(readiness["status"], "ready_for_explicit_install")
            self.assertTrue(readiness["install_target_preflight"]["valid"])
            self.assertEqual(readiness["install_target_preflight"]["path"], str(install_dir))
            self.assertEqual(readiness["install_target_preflight"]["route"], "skins_vehicles_stadiumcar")
            self.assertIn(shlex.quote(str(install_dir)), readiness["commands"]["install_explicit"])
            self.assertIn("install_with_explicit_target", readiness["next_actions"])
            self.assertFalse((install_dir / "calibration_stock_diffuse.zip").exists())

    def test_explicit_install_target_preflight_rejects_unrecognized_route(self):
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_kit import build_smoke_kit
        from src.evidence.smoke_readiness import build_smoke_readiness

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wrong_dir = root / "StadiumCar"
            wrong_dir.mkdir()
            build_smoke_kit(root / "out" / "proof" / "tmuf_calibration_smoke_kit")
            write_skin_dir_report(root / "out" / "proof" / "tmuf_skin_dirs.json", roots=[root / "missing"])

            readiness = build_smoke_readiness(root, install_target=wrong_dir)

            self.assertEqual(readiness["status"], "explicit_install_target_invalid")
            self.assertFalse(readiness["install_target_preflight"]["valid"])
            self.assertIn("unrecognized_stadiumcar_route", readiness["install_target_preflight"]["errors"])
            self.assertNotIn("run_tmuf_calibration_smoke_test", readiness["next_actions"])

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

    def test_cli_accepts_install_target_for_preflight(self):
        from recipes.smoke_readiness import main
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_kit import build_smoke_kit

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_dir = root / "Skins" / "Vehicles" / "StadiumCar"
            install_dir.mkdir(parents=True)
            build_smoke_kit(root / "out" / "proof" / "tmuf_calibration_smoke_kit")
            write_skin_dir_report(root / "out" / "proof" / "tmuf_skin_dirs.json", roots=[root / "missing"])

            output = main(["--root", str(root), "--install-target", str(install_dir), "--json"])
            data = json.loads(output)

            self.assertEqual(data["status"], "ready_for_explicit_install")
            self.assertEqual(data["install_target_preflight"]["path"], str(install_dir))
            self.assertIn(shlex.quote(str(install_dir)), data["commands"]["install_explicit"])

    def test_command_packet_is_human_readable_and_keeps_proof_boundary(self):
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS, REQUIRED_SCREENSHOT_ROLES
        from src.evidence.smoke_kit import build_smoke_kit
        from src.evidence.smoke_readiness import build_smoke_readiness
        from src.evidence.smoke_readiness import write_smoke_command_packet

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_path = root / "out" / "proof" / "tmuf_manual_smoke_commands.txt"
            build_smoke_kit(root / "out" / "proof" / "tmuf_calibration_smoke_kit")
            write_skin_dir_report(root / "out" / "proof" / "tmuf_skin_dirs.json", roots=[root / "missing"])

            written = write_smoke_command_packet(packet_path, root)
            readiness = build_smoke_readiness(root)

            self.assertEqual(written, packet_path)
            self.assertEqual(readiness["calibration_smoke_requirements"]["required_observations"], REQUIRED_OBSERVATIONS)
            self.assertEqual(readiness["calibration_smoke_requirements"]["required_screenshot_roles"], REQUIRED_SCREENSHOT_ROLES)
            self.assertTrue(readiness["calibration_smoke_requirements"]["does_not_prove_tmuf_smoke"])
            text = packet_path.read_text()
            self.assertIn("status=needs_explicit_stadiumcar_dir", text)
            self.assertIn("does_not_prove_tmuf_smoke=true", text)
            self.assertIn("Calibration observations to verify:", text)
            for observation in REQUIRED_OBSERVATIONS:
                self.assertIn(f"- {observation}", text)
            self.assertIn("Required screenshot roles:", text)
            for role in REQUIRED_SCREENSHOT_ROLES:
                self.assertIn(f"- {role}", text)
            self.assertIn("choose_or_create_tmuf_stadiumcar_skin_dir", text)
            self.assertIn("python3 recipes/prepare_tmuf_smoke_kit.py --install-skins-dir", text)
            self.assertIn("preflight_explicit:", text)
            self.assertIn("python3 recipes/smoke_readiness.py --install-target /absolute/path/to/StadiumCar", text)
            self.assertIn("scan_custom_root:", text)
            self.assertIn("python3 recipes/find_tmuf_skin_dirs.py --root /absolute/path/to/TrackMania-or-Wine-prefix", text)
            self.assertIn("scan_custom_root_bounded:", text)
            self.assertIn("--max-depth 8", text)
            self.assertIn("plan_creation_targets:", text)
            self.assertIn("--include-creation-targets", text)
            self.assertIn("create_explicit_target:", text)
            self.assertIn("python3 recipes/create_tmuf_skin_dir.py --target /absolute/path/to/StadiumCar --json", text)
            self.assertIn("create_and_install_explicit:", text)
            self.assertIn("--create-install-target", text)
            self.assertIn("Skins/Vehicles/StadiumCar", text)
            self.assertIn("GameData/Skins/Vehicles/StadiumCar", text)
            self.assertIn("Skins/Models/StadiumCar", text)
            self.assertIn("prepare_smoke_session:", text)
            self.assertIn("python3 recipes/prepare_tmuf_smoke_session.py --json", text)
            self.assertIn("prepare_premium_visual_review_session:", text)
            self.assertIn("python3 recipes/prepare_premium_visual_review_session.py --json", text)
            self.assertIn("install_premium_review_explicit:", text)
            self.assertIn("python3 recipes/install_premium_review_skins.py --install-skins-dir", text)
            self.assertIn("record_premium_visual_review:", text)
            self.assertIn("python3 recipes/record_premium_visual_review.py", text)
            self.assertIn("--skin-name black_magenta_cyan_blade", text)
            self.assertIn("--verdict needs_iteration", text)
            self.assertIn("python3 recipes/record_tmuf_smoke.py", text)
            self.assertIn("Do not run apply until evaluate passes", text)

    def test_command_packet_includes_explicit_install_target_preflight(self):
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_kit import build_smoke_kit
        from src.evidence.smoke_readiness import write_smoke_command_packet

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            install_dir = root / "Skins" / "Vehicles" / "StadiumCar"
            packet_path = root / "commands.txt"
            install_dir.mkdir(parents=True)
            build_smoke_kit(root / "out" / "proof" / "tmuf_calibration_smoke_kit")
            write_skin_dir_report(root / "out" / "proof" / "tmuf_skin_dirs.json", roots=[root / "missing"])

            write_smoke_command_packet(packet_path, root, install_target=install_dir)

            text = packet_path.read_text()
            self.assertIn("Install target preflight:", text)
            self.assertIn(f"path={install_dir}", text)
            self.assertIn("route=skins_vehicles_stadiumcar", text)
            self.assertIn("valid=true", text)
            self.assertIn("does_not_prove_tmuf_smoke=true", text)
            self.assertIn(
                f"python3 recipes/install_premium_review_skins.py --install-skins-dir {install_dir} --json",
                text,
            )

    def test_command_packet_includes_recommended_documents_trackmania_target(self):
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_kit import build_smoke_kit
        from src.evidence.smoke_readiness import build_smoke_readiness
        from src.evidence.smoke_readiness import write_smoke_command_packet

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            documents = root / "Documents"
            documents.mkdir()
            trackmania_root = documents / "TrackMania"
            packet_path = root / "commands.txt"
            build_smoke_kit(root / "out" / "proof" / "tmuf_calibration_smoke_kit")
            write_skin_dir_report(
                root / "out" / "proof" / "tmuf_skin_dirs.json",
                roots=[trackmania_root],
                include_creation_targets=True,
            )

            write_smoke_command_packet(packet_path, root)
            readiness = build_smoke_readiness(root)

            recommended_path = str(trackmania_root / "Skins" / "Vehicles" / "StadiumCar")
            self.assertEqual(readiness["skin_dirs"]["recommended_creation_target"]["path"], recommended_path)
            self.assertIn("preflight_recommended_creation_target", readiness["commands"])
            self.assertIn("create_and_install_recommended_creation_target", readiness["commands"])
            text = packet_path.read_text()
            self.assertIn("Recommended manual creation target:", text)
            self.assertIn(f"path={recommended_path}", text)
            self.assertIn("requires_root_creation=true", text)
            self.assertIn("preflight_recommended_creation_target:", text)
            self.assertIn("create_and_install_recommended_creation_target:", text)
            self.assertFalse(trackmania_root.exists())

    def test_cli_can_write_command_packet(self):
        from recipes.smoke_readiness import main
        from src.evidence.skin_dirs import write_skin_dir_report
        from src.evidence.smoke_kit import build_smoke_kit

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_path = root / "commands.txt"
            build_smoke_kit(root / "out" / "proof" / "tmuf_calibration_smoke_kit")
            write_skin_dir_report(root / "out" / "proof" / "tmuf_skin_dirs.json", roots=[root / "missing"])

            output = main(["--root", str(root), "--write-command-packet", str(packet_path)])

            self.assertTrue(packet_path.exists())
            self.assertIn("command_packet=", output)
            self.assertIn(str(packet_path), output)


if __name__ == "__main__":
    unittest.main()
