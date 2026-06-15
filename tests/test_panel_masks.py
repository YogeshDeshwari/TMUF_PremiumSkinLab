import unittest


class PanelMaskTests(unittest.TestCase):
    def test_named_psd_panel_masks_match_local_label_areas(self):
        from src.stock_diffuse.calibration import load_fields
        from src.stock_diffuse.panel_masks import build_stock_panel_masks

        masks = build_stock_panel_masks(load_fields())

        self.assertEqual(masks["main_body_top"].pixel_count, 1_622_702)
        self.assertEqual(masks["side_under_color"].pixel_count, 263_234)
        self.assertEqual(masks["tailwing"].pixel_count, 177_929)
        self.assertEqual(masks["mudguards"].pixel_count, 425_340)
        self.assertEqual(masks["nose_part"].pixel_count, 101_934)

        mudguard = masks["mudguards"]
        self.assertEqual(mudguard.evidence_status, "proven_local_psd_parts_label_map")
        self.assertEqual(mudguard.risk_class, "broad_design_surface")
        self.assertIn("FrontMudGuards", mudguard.source_zones)
        self.assertIn("RearMudGuards", mudguard.source_zones)

    def test_gbuffer_panel_masks_are_explicitly_experimental(self):
        from src.stock_diffuse.calibration import load_fields
        from src.stock_diffuse.panel_masks import build_stock_panel_masks

        fields = load_fields()
        coverage = fields["coverage"]
        masks = build_stock_panel_masks(fields)

        for name in (
            "center_spine",
            "nose_spear",
            "side_blade",
            "secondary_blade",
            "rear_louvers",
            "rear_center_glow",
            "shoulder_line",
            "tail_bar",
            "mudguard_edge",
        ):
            with self.subTest(name=name):
                panel = masks[name]
                self.assertEqual(panel.evidence_status, "experimental_until_tmuf_smoke")
                self.assertGreater(panel.pixel_count, 0)
                self.assertFalse((panel.mask & ~coverage).any())

    def test_generated_panel_family_masks_match_catalog_areas(self):
        from src.stock_diffuse.calibration import load_fields
        from src.stock_diffuse.panel_masks import build_stock_panel_masks

        masks = build_stock_panel_masks(load_fields())

        expected_areas = {
            "mid_deck_generated_panels": 723_443,
            "mid_side_generated_panel": 623_575,
            "nose_floor_generated_panels": 788_929,
            "rear_floor_generated_panels": 256_274,
            "rear_deck_fine_louver_rows": 272_437,
        }
        for name, expected_area in expected_areas.items():
            with self.subTest(name=name):
                panel = masks[name]
                self.assertEqual(panel.pixel_count, expected_area)
                self.assertEqual(panel.evidence_status, "mixed_generated_labels_and_experimental_gbuffer")
                self.assertTrue(any("panels_" in source for source in panel.source_files))
                self.assertIn("resources/authoritative/gbuffer/position_2048.npy", panel.source_files)

    def test_mask_report_entries_strip_arrays_but_keep_evidence(self):
        from src.stock_diffuse.calibration import load_fields
        from src.stock_diffuse.panel_masks import build_stock_panel_masks, mask_report_entries

        masks = build_stock_panel_masks(load_fields())
        report = mask_report_entries(masks, ["mudguards", "center_spine"])

        self.assertNotIn("mask", report["mudguards"])
        self.assertEqual(report["mudguards"]["pixel_count"], 425_340)
        self.assertEqual(report["mudguards"]["evidence_status"], "proven_local_psd_parts_label_map")
        self.assertEqual(report["center_spine"]["evidence_status"], "experimental_until_tmuf_smoke")
        self.assertIn("resources/authoritative/gbuffer/position_2048.npy", report["center_spine"]["source_files"])


if __name__ == "__main__":
    unittest.main()
