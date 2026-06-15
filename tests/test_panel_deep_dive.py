import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class StockPanelDeepDiveTests(unittest.TestCase):
    def test_deep_dive_groups_catalog_targets_without_runtime_claims(self):
        from src.evidence.panel_deep_dive import build_panel_deep_dive

        report = build_panel_deep_dive()

        self.assertEqual(report["schema"], "tmuf_premium_skin_lab.stock_panel_deep_dive.v1")
        self.assertEqual(report["evidence_boundary"]["tmuf_runtime_status"], "not_proven_until_smoke")
        self.assertIn("no roof named PSD zone", report["evidence_boundary"]["known_limits"])
        self.assertEqual(report["catalog_target_count"], 26)

        families = report["surface_families"]
        self.assertIn("nose_identity_panel", families["front_nose_centerline"]["targets"])
        self.assertIn("center_spine", families["front_nose_centerline"]["targets"])
        self.assertIn("mid_deck_generated_panels", families["cockpit_mid_deck"]["targets"])
        self.assertIn("engine_rear_deck", families["rear_engine_tail"]["targets"])
        self.assertIn("rear_deck_fine_louver_rows", families["rear_engine_tail"]["targets"])
        self.assertIn("rear_wheel_diffuse_blocks", families["support_auxiliary"]["targets"])

        for family in families.values():
            for entry in family["target_entries"]:
                self.assertIn("source_zones", entry)
                self.assertEqual(entry["tmuf_runtime_status"], "not_proven_until_smoke")
                self.assertNotIn("proved_in_tmuf", json.dumps(entry))

    def test_deep_dive_marks_underused_more_panel_opportunities(self):
        from src.evidence.panel_deep_dive import build_panel_deep_dive

        report = build_panel_deep_dive()
        opportunities = {entry["target"]: entry for entry in report["more_panel_opportunities"]}

        self.assertIn("mid_deck_generated_panels", opportunities)
        self.assertIn("black_cyan_spine", opportunities["mid_deck_generated_panels"]["candidate_usage"])
        self.assertIn("magenta_cyan_race_proto", opportunities["mid_deck_generated_panels"]["candidate_usage"])
        self.assertIn("cockpit", opportunities["mid_deck_generated_panels"]["why_it_matters"])

        self.assertIn("mid_side_generated_panel", opportunities)
        self.assertIn("violet_cyber_flow", opportunities["mid_side_generated_panel"]["candidate_usage"])
        self.assertIn("mid_side_C_02", opportunities["mid_side_generated_panel"]["source_zones"])

        for entry in opportunities.values():
            self.assertIn("tmuf smoke", " ".join(entry["proof_gates"]).lower())
            self.assertNotIn("runtime proven", json.dumps(entry).lower())

    def test_deep_dive_keeps_non_stock_routes_locked(self):
        from src.evidence.panel_deep_dive import build_panel_deep_dive

        report = build_panel_deep_dive()
        locked = {entry["route"]: entry for entry in report["locked_or_non_stock_routes"]}

        self.assertEqual(locked["details_dds"]["status"], "locked_custom_profile")
        self.assertEqual(locked["projshad_dds"]["status"], "locked_custom_profile")
        self.assertEqual(locked["custom_mesh_nomud"]["status"], "locked_custom_profile")
        self.assertIn("not stock_diffuse_only", " ".join(locked["details_dds"]["notes"]))
        self.assertIn("CH_2026", " ".join(locked["custom_mesh_nomud"]["proof_gates"]))

    def test_cli_writes_deep_dive_report_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            json_output = root / "stock_panel_deep_dive.json"
            markdown_output = root / "stock_panel_deep_dive.md"

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "recipes" / "explain_stock_panels.py"),
                    "--json-output",
                    str(json_output),
                    "--markdown-output",
                    str(markdown_output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn(str(json_output), result.stdout)
            self.assertIn(str(markdown_output), result.stdout)
            data = json.loads(json_output.read_text())
            self.assertEqual(data["schema"], "tmuf_premium_skin_lab.stock_panel_deep_dive.v1")
            markdown = markdown_output.read_text()
            self.assertIn("# Stock Panel Deep Dive", markdown)
            self.assertIn("front_nose_centerline", markdown)
            self.assertIn("Details.dds", markdown)


if __name__ == "__main__":
    unittest.main()
