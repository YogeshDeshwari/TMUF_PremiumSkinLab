import json
from pathlib import Path
import tempfile
import unittest


class SkinDirLocatorTests(unittest.TestCase):
    def test_finds_direct_stadiumcar_skin_directories_without_creating_paths(self):
        from src.evidence.skin_dirs import find_stadiumcar_skin_dirs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "Documents" / "TrackMania" / "Skins" / "Vehicles" / "StadiumCar"
            direct.mkdir(parents=True)
            (direct / "existing_skin.zip").write_bytes(b"skin")
            (root / "unrelated" / "StadiumCar").mkdir(parents=True)

            candidates = find_stadiumcar_skin_dirs([root])

            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["path"], direct.as_posix())
            self.assertEqual(candidates[0]["route"], "skins_vehicles_stadiumcar")
            self.assertEqual(candidates[0]["confidence"], "high")
            self.assertEqual(candidates[0]["existing_zip_count"], 1)

    def test_missing_roots_return_empty_candidates(self):
        from src.evidence.skin_dirs import find_stadiumcar_skin_dirs

        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"

            self.assertEqual(find_stadiumcar_skin_dirs([missing]), [])
            self.assertFalse(missing.exists())

    def test_max_depth_bounds_scan_and_report_records_boundary(self):
        from src.evidence.skin_dirs import build_skin_dir_report, find_stadiumcar_skin_dirs

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shallow = root / "Skins" / "Vehicles" / "StadiumCar"
            deep = root / "prefix" / "nested" / "Skins" / "Vehicles" / "StadiumCar"
            shallow.mkdir(parents=True)
            deep.mkdir(parents=True)

            bounded = find_stadiumcar_skin_dirs([root], max_depth=3)
            unbounded = find_stadiumcar_skin_dirs([root])
            report = build_skin_dir_report([root], max_depth=3)

            self.assertEqual([item["path"] for item in bounded], [shallow.as_posix()])
            self.assertEqual(sorted(item["path"] for item in unbounded), sorted([shallow.as_posix(), deep.as_posix()]))
            self.assertEqual(report["scan_boundary"]["max_depth"], 3)
            self.assertTrue(report["scan_boundary"]["bounded_by_max_depth"])
            self.assertTrue(report["scan_boundary"]["does_not_prove_tmuf_smoke"])

    def test_report_can_include_manual_creation_targets_without_creating_paths(self):
        from src.evidence.skin_dirs import KNOWN_SUFFIXES, build_skin_dir_report

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "TMUF UserData"
            root.mkdir()

            report = build_skin_dir_report([root], include_creation_targets=True)

            self.assertEqual(report["candidate_count"], 0)
            targets = report["manual_creation_targets"]
            self.assertEqual(len(targets), len(KNOWN_SUFFIXES))
            self.assertTrue(report["does_not_prove_tmuf_smoke"])
            for target in targets:
                path = Path(target["path"])
                self.assertFalse(path.exists())
                self.assertTrue(target["requires_manual_creation"])
                self.assertTrue(target["does_not_prove_tmuf_smoke"])
                self.assertEqual(target["status"], "manual_target_hint_not_tmuf_proof")
                self.assertEqual(target["target_root"], root.as_posix())
                self.assertIn(target["route"], set(KNOWN_SUFFIXES.values()))

    def test_cli_can_write_candidate_report(self):
        from recipes.find_tmuf_skin_dirs import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            direct = root / "Skins" / "Vehicles" / "StadiumCar"
            direct.mkdir(parents=True)
            out = root / "skin_dirs.json"

            output = main(["--root", str(root), "--write", str(out), "--json"])
            data = json.loads(output)

            self.assertEqual(data["candidate_count"], 1)
            self.assertEqual(data["candidates"][0]["path"], direct.as_posix())
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text())["candidate_count"], 1)

    def test_cli_can_limit_scan_depth(self):
        from recipes.find_tmuf_skin_dirs import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shallow = root / "Skins" / "Vehicles" / "StadiumCar"
            deep = root / "prefix" / "nested" / "Skins" / "Vehicles" / "StadiumCar"
            shallow.mkdir(parents=True)
            deep.mkdir(parents=True)

            output = main(["--root", str(root), "--max-depth", "3", "--json"])
            data = json.loads(output)

            self.assertEqual(data["candidate_count"], 1)
            self.assertEqual(data["candidates"][0]["path"], shallow.as_posix())
            self.assertEqual(data["scan_boundary"]["max_depth"], 3)

    def test_cli_can_emit_manual_creation_targets_for_explicit_root(self):
        from recipes.find_tmuf_skin_dirs import main

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "TMUF Prefix"
            root.mkdir()

            output = main(["--root", str(root), "--include-creation-targets", "--json"])
            data = json.loads(output)

            self.assertEqual(data["candidate_count"], 0)
            self.assertGreaterEqual(len(data["manual_creation_targets"]), 3)
            self.assertTrue(all(item["path"].startswith(root.as_posix()) for item in data["manual_creation_targets"]))
            self.assertTrue(all(item["requires_manual_creation"] for item in data["manual_creation_targets"]))
            self.assertFalse(any(Path(item["path"]).exists() for item in data["manual_creation_targets"]))


if __name__ == "__main__":
    unittest.main()
