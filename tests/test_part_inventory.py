import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class StockPartInventoryTests(unittest.TestCase):
    def test_inventory_records_all_local_label_maps(self):
        from src.evidence.part_inventory import build_part_inventory

        inventory = build_part_inventory()
        self.assertEqual(inventory["evidence_status"]["psd_parts"], "proven_local_label_map")
        self.assertEqual(inventory["evidence_status"]["panels_high"], "proven_local_label_map_generated_names")
        self.assertEqual(inventory["evidence_status"]["gbuffer"], "experimental_until_tmuf_smoke")

        label_maps = inventory["label_maps"]
        self.assertEqual(label_maps["psd_parts"]["zone_count"], 41)
        self.assertEqual(label_maps["panels_high"]["zone_count"], 60)
        self.assertEqual(label_maps["panels_fine"]["zone_count"], 107)
        for label_map in label_maps.values():
            self.assertEqual(label_map["shape"], [2048, 2048])
            self.assertTrue(label_map["json_ids_match_label_map_ids"])
            self.assertGreater(label_map["atlas_coverage_ratio"], 0.97)

    def test_inventory_classifies_broad_and_probe_only_zones(self):
        from src.evidence.part_inventory import build_part_inventory

        inventory = build_part_inventory()
        psd_by_name = {zone["name"]: zone for zone in inventory["label_maps"]["psd_parts"]["zones"]}
        fine_by_name = {zone["name"]: zone for zone in inventory["label_maps"]["panels_fine"]["zones"]}

        self.assertEqual(psd_by_name["MainBodyTOP_BR"]["risk_class"], "broad_design_surface")
        self.assertEqual(psd_by_name["NosePart"]["risk_class"], "broad_design_surface")
        self.assertEqual(psd_by_name["MirrorHolders"]["risk_class"], "small_detail_surface")
        self.assertEqual(fine_by_name["rear_deck_C_142"]["risk_class"], "probe_only_tiny_fragment")

    def test_inventory_records_mesh_and_gbuffer_projection_evidence(self):
        from src.evidence.part_inventory import build_part_inventory

        inventory = build_part_inventory()
        self.assertEqual(inventory["gbuffer"]["axis_roles"], {"LAT": 0, "HGT": 1, "LEN": 2})
        self.assertEqual(inventory["gbuffer"]["coverage_values"], [0, 255])
        self.assertEqual(inventory["gbuffer"]["covered_pixels"], 2750624)
        self.assertTrue(inventory["mesh"]["all_faces_have_uvs"])
        self.assertGreaterEqual(inventory["mesh"]["component_count"], 13)
        self.assertIn("front_nose_len_positive", inventory["targetable_regions"])
        self.assertIn("rear_deck_candidate_len_negative_high_hgt", inventory["targetable_regions"])

    def test_inventory_exposes_paintable_panel_catalog_with_evidence_boundaries(self):
        from src.evidence.part_inventory import build_part_inventory

        inventory = build_part_inventory()
        catalog = inventory["paintable_panel_catalog"]

        self.assertEqual(catalog["schema"], "tmuf_premium_skin_lab.paintable_panel_catalog.v1")
        self.assertEqual(catalog["tmuf_runtime_status"], "not_proven_until_smoke")
        self.assertIn("no panel entry proves TMUF runtime visibility before calibration smoke", catalog["boundary"])

        panels = catalog["panels"]
        self.assertGreaterEqual(len(panels), 12)

        tailwing = panels["tailwing_bands"]
        self.assertEqual(tailwing["source_status"], "proven_local_label_map")
        self.assertEqual(tailwing["tmuf_runtime_status"], "not_proven_until_smoke")
        self.assertIn("TailWingUnderBorderColor", tailwing["source_zones"])
        self.assertIn("resources/authoritative/parts/psd_parts.json", tailwing["source_files"])

        rear_deck = panels["engine_rear_deck"]
        self.assertEqual(rear_deck["source_status"], "mixed_generated_labels_and_experimental_gbuffer")
        self.assertIn("rear_deck_C_63", rear_deck["source_zones"])
        self.assertIn("resources/authoritative/parts/panels_high.json", rear_deck["source_files"])
        self.assertIn("resources/authoritative/gbuffer/position_2048.npy", rear_deck["source_files"])

        front_guards = panels["front_mudguard_caps"]
        self.assertEqual(front_guards["source_status"], "mixed_local_label_and_experimental_gbuffer")
        self.assertIn("FrontMudGuards", front_guards["source_zones"])
        self.assertIn("LEN/Z front split remains experimental until TMUF smoke", front_guards["proof_notes"])

        center_spine = panels["center_spine"]
        self.assertEqual(center_spine["source_status"], "experimental_until_tmuf_smoke")
        self.assertIn("LAT/X symmetry", center_spine["geometry_constraints"])
        self.assertEqual(center_spine["safe_design_scale"], "medium_to_broad_accent")

    def test_cli_writes_inventory_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "stock_part_inventory.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "recipes" / "explore_stock_parts.py"),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn(str(output), result.stdout)
            data = json.loads(output.read_text())
            self.assertEqual(data["label_maps"]["psd_parts"]["zone_count"], 41)
            self.assertIn("no_tmuf_runtime_visibility_claim", data["unknowns"])


if __name__ == "__main__":
    unittest.main()
