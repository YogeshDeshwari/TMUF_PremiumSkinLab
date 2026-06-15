import json
import unittest


class StockValidatorTests(unittest.TestCase):
    def test_current_stock_outputs_pass_local_checks_but_keep_smoke_pending(self):
        from src.evidence.stock_validator import REQUIRED_STOCK_SKINS, validate_stock_outputs

        result = validate_stock_outputs()

        self.assertTrue(result["local_checks_passed"])
        self.assertEqual(result["completion_status"], "not_complete_tmuf_smoke_pending")
        self.assertEqual(result["tmuf_smoke_status"], "pending")
        self.assertEqual(result["errors"], [])
        self.assertIn("tmuf_smoke_pending", result["warnings"])
        self.assertEqual([skin["skin_name"] for skin in result["skins"]], REQUIRED_STOCK_SKINS)

        for skin in result["skins"]:
            checks = skin["checks"]
            self.assertTrue(checks["zip_exists"])
            self.assertTrue(checks["zip_stock_diffuse_only"])
            self.assertTrue(checks["zip_has_stable_timestamps"])
            self.assertTrue(checks["dds_headers_valid"])
            self.assertTrue(checks["report_exists"])
            self.assertTrue(checks["report_route_stock_diffuse_only"])
            self.assertTrue(checks["report_declares_no_donor_or_details_route"])
            self.assertTrue(checks["report_input_evidence_matches_manifest"])
            self.assertTrue(checks["report_output_artifacts_match_files"])
            self.assertTrue(checks["report_mask_evidence_valid"])
            self.assertTrue(checks["report_design_lane_valid"])
            self.assertTrue(checks["report_panel_catalog_targets_valid"])
            self.assertTrue(checks["report_render_profile_valid"])
            self.assertTrue(checks["atlas_preview_exists"])
            self.assertTrue(checks["projection_preview_exists"])
            self.assertTrue(checks["preview_visual_quality_passed"])
            self.assertFalse(checks["tmuf_smoke_passed"])
            self.assertIn("visual_metrics", skin)

        premium_lanes = [
            skin["design_lane"]["lane_id"]
            for skin in result["skins"]
            if skin["skin_name"] != "calibration_stock_diffuse"
        ]
        self.assertEqual(len(set(premium_lanes)), len(premium_lanes))
        self.assertTrue(result["premium_batch_index"]["valid"])
        self.assertEqual(result["premium_batch_index"]["candidate_count"], 5)
        self.assertTrue(result["premium_batch_index"]["does_not_prove_tmuf_smoke"])

    def test_report_input_evidence_must_match_manifest(self):
        from src.evidence.input_trace import STOCK_DIFFUSE_INPUTS
        from src.evidence.stock_validator import validate_input_evidence

        manifest = {
            "resources": [
                {
                    "path": path,
                    "evidence_label": "proven",
                    "sha256": f"{index:064x}",
                    "size_bytes": index + 1,
                }
                for index, path in enumerate(STOCK_DIFFUSE_INPUTS)
            ]
        }
        report = {"input_evidence": {}}

        errors = validate_input_evidence(report, manifest)

        self.assertEqual(len(errors), len(STOCK_DIFFUSE_INPUTS))
        self.assertTrue(all(error.startswith("missing input evidence:") for error in errors))

        report["input_evidence"] = {
            path: {
                "evidence_label": entry["evidence_label"],
                "sha256": entry["sha256"],
                "size_bytes": entry["size_bytes"],
            }
            for path, entry in [(item["path"], item) for item in manifest["resources"]]
        }
        self.assertEqual(validate_input_evidence(report, manifest), [])

        first = STOCK_DIFFUSE_INPUTS[0]
        report["input_evidence"][first]["sha256"] = "bad"
        self.assertEqual(
            validate_input_evidence(report, manifest),
            [f"input evidence sha256 mismatch: {first}"],
        )

    def test_premium_report_mask_evidence_is_validated(self):
        from src.evidence.stock_validator import validate_mask_evidence

        valid_report = {
            "skin_name": "example",
            "tmuf_smoke_test": "not_run",
            "evidence_status": {"gbuffer_mapping": "experimental_until_tmuf_smoke"},
            "masks_used": ["mudguards", "tailwing", "center_spine"],
            "mask_evidence": {
                "mudguards": {
                    "evidence_status": "proven_local_psd_parts_label_map",
                    "pixel_count": 425340,
                    "source_files": ["resources/authoritative/parts/psd_parts_labels.npy"],
                },
                "tailwing": {
                    "evidence_status": "proven_local_psd_parts_label_map",
                    "pixel_count": 177929,
                    "source_files": ["resources/authoritative/parts/psd_parts_labels.npy"],
                },
                "center_spine": {
                    "evidence_status": "experimental_until_tmuf_smoke",
                    "pixel_count": 531368,
                    "source_files": ["resources/authoritative/gbuffer/position_2048.npy"],
                },
            },
        }
        self.assertEqual(validate_mask_evidence(valid_report, premium=True), [])
        self.assertEqual(validate_mask_evidence(valid_report, premium=False), [])

        promoted_report = {
            **valid_report,
            "tmuf_smoke_test": "passed",
            "evidence_status": {"gbuffer_mapping": "proven_by_tmuf_smoke"},
            "mask_evidence": {
                **valid_report["mask_evidence"],
                "center_spine": {
                    **valid_report["mask_evidence"]["center_spine"],
                    "evidence_status": "proven_by_tmuf_smoke",
                },
            },
        }
        self.assertEqual(validate_mask_evidence(promoted_report, premium=True), [])

        premature_report = {
            **valid_report,
            "mask_evidence": {
                **valid_report["mask_evidence"],
                "center_spine": {
                    **valid_report["mask_evidence"]["center_spine"],
                    "evidence_status": "proven_by_tmuf_smoke",
                },
            },
        }
        self.assertIn(
            "center_spine must stay experimental until TMUF smoke",
            validate_mask_evidence(premature_report, premium=True),
        )

        bad_local_source_report = {
            **valid_report,
            "mask_evidence": {
                **valid_report["mask_evidence"],
                "tailwing": {
                    **valid_report["mask_evidence"]["tailwing"],
                    "source_files": ["resources/authoritative/gbuffer/position_2048.npy"],
                },
            },
        }
        self.assertIn(
            "tailwing local PSD mask must cite psd_parts_labels.npy",
            validate_mask_evidence(bad_local_source_report, premium=True),
        )

        mixed_generated_report = {
            **valid_report,
            "masks_used": ["mudguards", "mid_deck_generated_panels"],
            "mask_evidence": {
                "mudguards": valid_report["mask_evidence"]["mudguards"],
                "mid_deck_generated_panels": {
                    "evidence_status": "mixed_generated_labels_and_experimental_gbuffer",
                    "pixel_count": 723443,
                    "source_files": [
                        "resources/authoritative/parts/panels_high_labels.npy",
                        "resources/authoritative/gbuffer/position_2048.npy",
                    ],
                },
            },
        }
        self.assertEqual(validate_mask_evidence(mixed_generated_report, premium=True), [])

        broken_report = {
            "skin_name": "broken",
            "masks_used": ["mudguards", "center_spine"],
            "mask_evidence": {
                "mudguards": {
                    "evidence_status": "experimental_until_tmuf_smoke",
                    "pixel_count": 425340,
                    "source_files": ["resources/authoritative/gbuffer/position_2048.npy"],
                }
            },
        }

        errors = validate_mask_evidence(broken_report, premium=True)

        self.assertIn("missing mask evidence: center_spine", errors)
        self.assertIn("mudguards must use proven local PSD label evidence", errors)

    def test_premium_report_alpha_policy_is_validated_without_gloss_claims(self):
        from src.evidence.stock_validator import validate_alpha_policy

        valid_report = {
            "skin_name": "example",
            "alpha_policy": {
                "route": "conservative_dxt5_alpha",
                "material_effect_status": "not_proven_until_tmuf_smoke",
                "tmuf_gloss_claim": "none",
            },
            "alpha_metrics": {
                "min_alpha": 112,
                "max_alpha": 148,
                "mean_alpha": 121.5,
                "unique_alpha_values": [112, 118, 136, 148],
                "high_alpha_pixel_ratio": 0.19,
            },
        }

        self.assertEqual(validate_alpha_policy(valid_report, premium=True), [])
        self.assertEqual(validate_alpha_policy(valid_report, premium=False), [])

        gloss_claim = {
            **valid_report,
            "alpha_policy": {
                **valid_report["alpha_policy"],
                "material_effect_status": "proven_gloss",
                "tmuf_gloss_claim": "gloss",
            },
        }
        errors = validate_alpha_policy(gloss_claim, premium=True)
        self.assertIn("alpha material effect must remain unproven until TMUF smoke", errors)
        self.assertIn("alpha policy must not claim TMUF gloss behavior", errors)

        too_extreme = {
            **valid_report,
            "alpha_metrics": {
                **valid_report["alpha_metrics"],
                "min_alpha": 0,
                "max_alpha": 255,
            },
        }
        errors = validate_alpha_policy(too_extreme, premium=True)
        self.assertIn("alpha min below conservative range", errors)
        self.assertIn("alpha max above conservative range", errors)

    def test_premium_design_lane_evidence_is_validated(self):
        from src.evidence.stock_validator import validate_design_lane_evidence, validate_premium_lane_distinctness

        valid_report = {
            "skin_name": "example",
            "masks_used": ["center_spine", "tailwing", "mudguard_edge"],
            "design_lane": {
                "lane_id": "center_spine_focus",
                "composition_focus": "dominant center spine with restrained local panel echoes",
                "distinctive_masks": ["center_spine", "tailwing"],
                "evidence_status": "recipe_metadata_not_tmuf_proof",
            },
        }
        self.assertEqual(validate_design_lane_evidence(valid_report, premium=True), [])
        self.assertEqual(validate_design_lane_evidence(valid_report, premium=False), [])

        missing_lane = {"skin_name": "missing", "masks_used": ["center_spine"]}
        self.assertEqual(
            validate_design_lane_evidence(missing_lane, premium=True),
            ["premium report has no design_lane object"],
        )

        bad_status = {
            **valid_report,
            "design_lane": {
                **valid_report["design_lane"],
                "evidence_status": "proven_by_tmuf_smoke",
            },
        }
        self.assertIn(
            "design lane metadata must not claim TMUF proof",
            validate_design_lane_evidence(bad_status, premium=True),
        )

        bad_mask = {
            **valid_report,
            "design_lane": {
                **valid_report["design_lane"],
                "distinctive_masks": ["center_spine", "not_a_used_mask"],
            },
        }
        self.assertIn(
            "design lane distinctive masks must be listed in masks_used",
            validate_design_lane_evidence(bad_mask, premium=True),
        )

        duplicate_lanes = [
            {"skin_name": "a", "design_lane": {"lane_id": "same"}},
            {"skin_name": "b", "design_lane": {"lane_id": "same"}},
        ]
        self.assertEqual(
            validate_premium_lane_distinctness(duplicate_lanes),
            ["premium design lanes must be distinct across candidates"],
        )

    def test_premium_panel_catalog_targets_are_validated(self):
        from src.evidence.stock_validator import validate_panel_catalog_targets

        valid_report = {
            "skin_name": "example",
            "panel_catalog_targets": ["center_spine", "tailwing_bands", "underbody_dark"],
            "design_lane": {
                "primary_catalog_targets": ["center_spine", "tailwing_bands", "underbody_dark"],
                "catalog_target_count": 3,
            },
        }
        self.assertEqual(validate_panel_catalog_targets(valid_report, premium=True), [])
        self.assertEqual(validate_panel_catalog_targets(valid_report, premium=False), [])

        missing_targets = {"skin_name": "missing", "design_lane": {}}
        self.assertEqual(
            validate_panel_catalog_targets(missing_targets, premium=True),
            ["premium report has no panel_catalog_targets list"],
        )

        unknown_target = {
            **valid_report,
            "panel_catalog_targets": ["center_spine", "not_in_catalog"],
            "design_lane": {
                **valid_report["design_lane"],
                "primary_catalog_targets": ["center_spine", "not_in_catalog"],
                "catalog_target_count": 2,
            },
        }
        self.assertIn(
            "unknown panel catalog target: not_in_catalog",
            validate_panel_catalog_targets(unknown_target, premium=True),
        )

        mismatched_lane = {
            **valid_report,
            "design_lane": {
                "primary_catalog_targets": ["center_spine"],
                "catalog_target_count": 1,
            },
        }
        errors = validate_panel_catalog_targets(mismatched_lane, premium=True)
        self.assertIn("design lane primary_catalog_targets must match panel_catalog_targets", errors)
        self.assertIn("design lane catalog_target_count must match panel_catalog_targets", errors)

    def test_premium_render_profile_is_validated(self):
        from src.evidence.stock_validator import validate_render_profile

        valid_report = {
            "skin_name": "example",
            "masks_used": ["center_spine", "side_blade", "tailwing", "mid_deck_generated_panels"],
            "design_lane": {
                "distinctive_masks": ["center_spine", "tailwing"],
            },
            "render_profile": {
                "lane_specific_strengths": True,
                "evidence_status": "recipe_metadata_not_tmuf_proof",
                "mask_strengths": {
                    "center_spine": 1.2,
                    "side_blade": 0.7,
                    "tailwing": 1.1,
                    "mid_deck_generated_panels": 1.0,
                },
                "panel_family_strengths": {
                    "mid_deck_generated_panels": 1.0,
                },
                "distinctive_mask_strengths": {
                    "center_spine": 1.2,
                    "tailwing": 1.1,
                },
                "damped_masks": ["side_blade"],
            },
            "mask_style_metrics": {
                "center_spine": {"pixel_count": 100, "mean_alpha": 148.0},
                "side_blade": {"pixel_count": 100, "mean_alpha": 112.0},
                "tailwing": {"pixel_count": 100, "mean_alpha": 136.0},
                "mid_deck_generated_panels": {"pixel_count": 100, "mean_alpha": 124.0},
            },
        }
        self.assertEqual(validate_render_profile(valid_report, premium=True), [])
        self.assertEqual(validate_render_profile(valid_report, premium=False), [])

        missing_profile = {"skin_name": "missing", "masks_used": ["center_spine"]}
        self.assertEqual(
            validate_render_profile(missing_profile, premium=True),
            ["premium report has no render_profile object"],
        )

        bad_status = {
            **valid_report,
            "render_profile": {
                **valid_report["render_profile"],
                "evidence_status": "proven_by_tmuf_smoke",
            },
        }
        self.assertIn(
            "render profile metadata must not claim TMUF proof",
            validate_render_profile(bad_status, premium=True),
        )

        missing_panel_family_strengths = {
            **valid_report,
            "render_profile": {
                key: value
                for key, value in valid_report["render_profile"].items()
                if key != "panel_family_strengths"
            },
        }
        self.assertIn(
            "render profile has no panel_family_strengths object",
            validate_render_profile(missing_panel_family_strengths, premium=True),
        )

        missing_metric = {
            **valid_report,
            "mask_style_metrics": {
                "center_spine": {"pixel_count": 100, "mean_alpha": 148.0},
            },
        }
        self.assertIn(
            "missing mask style metrics: tailwing",
            validate_render_profile(missing_metric, premium=True),
        )

    def test_premium_batch_index_is_validated_against_reports(self):
        from src.evidence.stock_validator import validate_premium_batch_index

        reports = [
            {
                "skin_name": "a",
                "route": "stock_diffuse_only",
                "package_files": ["Diffuse.dds", "Icon.dds"],
                "tmuf_smoke_test": "not_run",
                "evidence_status": {"gbuffer_mapping": "experimental_until_tmuf_smoke"},
                "design_lane": {"lane_id": "lane_a"},
                "render_profile": {"lane_specific_strengths": True},
                "panel_catalog_targets": ["center_spine"],
                "output_artifacts": {"skin_zip": {"path": "out/skins/a.zip"}},
            },
            {
                "skin_name": "b",
                "route": "stock_diffuse_only",
                "package_files": ["Diffuse.dds", "Icon.dds"],
                "tmuf_smoke_test": "not_run",
                "evidence_status": {"gbuffer_mapping": "experimental_until_tmuf_smoke"},
                "design_lane": {"lane_id": "lane_b"},
                "render_profile": {"lane_specific_strengths": True},
                "panel_catalog_targets": ["tailwing_bands"],
                "output_artifacts": {"skin_zip": {"path": "out/skins/b.zip"}},
            },
        ]
        valid_index = {
            "schema": "tmuf_premium_skin_lab.premium_batch_index.v1",
            "route": "stock_diffuse_only",
            "does_not_prove_tmuf_smoke": True,
            "candidate_count": 2,
            "candidates": [
                {
                    "skin_name": "a",
                    "tmuf_smoke_test": "not_run",
                    "gbuffer_mapping": "experimental_until_tmuf_smoke",
                    "design_lane": {"lane_id": "lane_a"},
                    "render_profile": {"lane_specific_strengths": True},
                    "panel_catalog_targets": ["center_spine"],
                    "package_files": ["Diffuse.dds", "Icon.dds"],
                    "output_artifacts": {"skin_zip": {"path": "out/skins/a.zip"}},
                },
                {
                    "skin_name": "b",
                    "tmuf_smoke_test": "not_run",
                    "gbuffer_mapping": "experimental_until_tmuf_smoke",
                    "design_lane": {"lane_id": "lane_b"},
                    "render_profile": {"lane_specific_strengths": True},
                    "panel_catalog_targets": ["tailwing_bands"],
                    "package_files": ["Diffuse.dds", "Icon.dds"],
                    "output_artifacts": {"skin_zip": {"path": "out/skins/b.zip"}},
                },
            ],
        }

        self.assertEqual(validate_premium_batch_index(valid_index, reports), [])

        duplicate = {
            **valid_index,
            "candidates": [
                valid_index["candidates"][0],
                {**valid_index["candidates"][1], "design_lane": {"lane_id": "lane_a"}},
            ],
        }
        self.assertIn(
            "premium batch index lane IDs must be distinct",
            validate_premium_batch_index(duplicate, reports),
        )

        wrong_count = {**valid_index, "candidate_count": 3}
        self.assertEqual(
            validate_premium_batch_index(wrong_count, reports),
            ["premium batch index candidate_count mismatch"],
        )

        wrong_targets = {
            **valid_index,
            "candidates": [
                {**valid_index["candidates"][0], "panel_catalog_targets": ["tailwing_bands"]},
                valid_index["candidates"][1],
            ],
        }
        self.assertIn(
            "premium batch index panel catalog targets mismatch: a",
            validate_premium_batch_index(wrong_targets, reports),
        )

        wrong_render_profile = {
            **valid_index,
            "candidates": [
                {
                    **valid_index["candidates"][0],
                    "render_profile": {"lane_specific_strengths": False},
                },
                valid_index["candidates"][1],
            ],
        }
        self.assertIn(
            "premium batch index render profile mismatch: a",
            validate_premium_batch_index(wrong_render_profile, reports),
        )

    def test_cli_outputs_json_summary(self):
        from recipes.validate_stock_outputs import main

        output = main(["--json"])
        data = json.loads(output)

        self.assertTrue(data["local_checks_passed"])
        self.assertEqual(data["tmuf_smoke_status"], "pending")


if __name__ == "__main__":
    unittest.main()
