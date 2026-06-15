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


if __name__ == "__main__":
    unittest.main()
