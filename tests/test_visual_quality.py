from pathlib import Path
import json
import tempfile
import unittest

from PIL import Image


class VisualQualityTests(unittest.TestCase):
    def test_current_premium_candidates_have_local_visual_quality_metrics(self):
        from src.evidence.stock_validator import validate_stock_outputs
        from src.stock_diffuse.premium import CANDIDATE_NAMES

        result = validate_stock_outputs()
        by_name = {skin["skin_name"]: skin for skin in result["skins"]}

        for name in CANDIDATE_NAMES:
            checks = by_name[name]["checks"]
            metrics = by_name[name]["visual_metrics"]

            self.assertTrue(checks["preview_visual_quality_passed"])
            self.assertTrue(checks["premium_style_quality_passed"])
            self.assertGreaterEqual(metrics["atlas_nonblank_ratio"], 0.50)
            self.assertGreaterEqual(metrics["projection_nonblank_ratio"], 0.50)
            self.assertGreaterEqual(metrics["atlas_contrast"], 60.0)
            self.assertGreaterEqual(metrics["projection_contrast"], 60.0)
            self.assertGreaterEqual(metrics["atlas_magenta_ratio"], 0.02)
            self.assertGreaterEqual(metrics["atlas_cyan_ratio"], 0.02)
            self.assertGreaterEqual(metrics["largest_accent_component_pixels"], 50000)

    def test_visual_quality_rejects_blank_preview(self):
        from src.evidence.visual_quality import validate_visual_quality

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "out" / "previews").mkdir(parents=True)
            Image.new("RGB", (64, 64), (0, 0, 0)).save(root / "out" / "previews" / "bad_atlas.png")
            Image.new("RGB", (64, 64), (0, 0, 0)).save(
                root / "out" / "previews" / "bad_projected_side_top_rear.png"
            )

            checks, metrics, errors = validate_visual_quality(root, "bad", premium=False)

            self.assertFalse(checks["preview_visual_quality_passed"])
            self.assertIn("atlas preview appears blank/too sparse: bad", errors)
            self.assertIn("projection preview appears blank/too sparse: bad", errors)
            self.assertEqual(metrics["atlas_nonblank_ratio"], 0.0)
            self.assertEqual(metrics["projection_nonblank_ratio"], 0.0)

    def test_premium_batch_index_carries_review_board_artifact(self):
        root = Path(__file__).resolve().parents[1]
        index = json.loads((root / "out" / "reports" / "premium_batch_index.json").read_text())

        review_board = index["visual_review_board"]
        self.assertEqual(review_board["path"], "out/previews/premium_candidate_review_board.png")
        board_path = root / review_board["path"]
        self.assertTrue(board_path.exists())
        self.assertRegex(review_board["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(review_board["size_bytes"], board_path.stat().st_size)
        with Image.open(board_path) as image:
            rgb = image.convert("RGB")
            self.assertGreaterEqual(rgb.width, 900)
            self.assertGreaterEqual(rgb.height, 900)
            self.assertTrue(any(channel_min != channel_max for channel_min, channel_max in rgb.getextrema()))
        self.assertTrue(index["visual_review_board_policy"]["does_not_prove_tmuf_smoke"])
        self.assertEqual(index["visual_review_board_policy"]["review_scope"], "local_candidate_comparison_only")


if __name__ == "__main__":
    unittest.main()
