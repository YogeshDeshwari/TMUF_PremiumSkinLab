import json
import hashlib
import struct
import zipfile
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
EXPECTED_ZIP_TIMESTAMP = (2000, 1, 1, 0, 0, 0)
EXPECTED_STOCK_INPUTS = {
    "authoritative/gbuffer/position_2048.npy": "experimental",
    "authoritative/gbuffer/coverage_2048.npy": "experimental",
    "authoritative/gbuffer/extents_2048.json": "experimental",
    "authoritative/parts/psd_parts_labels.npy": "proven",
    "authoritative/parts/psd_parts.json": "proven",
    "authoritative/reference/official_prelight_AO.png": "proven",
}
EXPECTED_PREMIUM_STOCK_INPUTS = {
    **EXPECTED_STOCK_INPUTS,
    "authoritative/parts/panels_high_labels.npy": "proven",
    "authoritative/parts/panels_high.json": "proven",
    "authoritative/parts/panels_fine_labels.npy": "proven",
    "authoritative/parts/panels_fine.json": "proven",
}
EXPECTED_OUTPUT_ARTIFACTS = {
    "skin_zip": "out/skins/{name}.zip",
    "atlas_preview": "out/previews/{name}_atlas.png",
    "projected_preview": "out/previews/{name}_projected_side_top_rear.png",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def dds_info(data: bytes):
    if data[:4] != b"DDS ":
        raise AssertionError("not a DDS file")
    height = struct.unpack("<I", data[12:16])[0]
    width = struct.unpack("<I", data[16:20])[0]
    mip_count = struct.unpack("<I", data[28:32])[0]
    fourcc = data[84:88].decode("ascii", errors="replace")
    return {"width": width, "height": height, "fourcc": fourcc, "mip_count": mip_count}


class EvidenceManifestTests(unittest.TestCase):
    def test_manifest_records_required_evidence_classes(self):
        manifest_path = ROOT / "resources" / "evidence_manifest.json"
        self.assertTrue(manifest_path.exists())

        data = json.loads(manifest_path.read_text())
        labels = {entry["evidence_label"] for entry in data["resources"]}
        self.assertGreaterEqual(labels, {"proven", "reference_only", "experimental"})

        by_name = {Path(entry["path"]).name: entry for entry in data["resources"]}
        self.assertEqual(by_name["official_StadiumCar_template.psd"]["evidence_label"], "proven")
        self.assertEqual(by_name["position_2048.npy"]["evidence_label"], "experimental")
        self.assertEqual(by_name["StadiumCarV2_primary_skin.zip"]["evidence_label"], "reference_only")
        self.assertEqual(
            by_name["CH_2026_NOT_STOCK_STADIUM_DETAILS_CUSTOM_MESH.zip"]["evidence_label"],
            "experimental",
        )
        self.assertEqual(by_name["CH_Blu.zip"]["evidence_label"], "reference_only")
        self.assertIn("CH_2026 custom full-car reference", by_name["CH_Blu.zip"]["safe_use"])
        self.assertIn("not stock Diffuse-only truth", by_name["CH_Blu.zip"]["limits"])
        self.assertEqual(by_name["CH_Bloom_Wheel_LED_Underglow.zip"]["evidence_label"], "reference_only")
        self.assertIn(
            "CH_2026 custom full-car reference",
            by_name["CH_Bloom_Wheel_LED_Underglow.zip"]["safe_use"],
        )

        for entry in data["resources"]:
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(entry["size_bytes"], 0)
            self.assertIn("safe_use", entry)
            self.assertIn("limits", entry)

    def test_manifest_excludes_regenerable_build_intermediates(self):
        manifest_path = ROOT / "resources" / "evidence_manifest.json"
        data = json.loads(manifest_path.read_text())
        paths = [entry["path"] for entry in data["resources"]]

        self.assertFalse(any("/bin/Debug/" in path for path in paths))
        self.assertFalse(any("/obj/" in path for path in paths))


class CalibrationArtifactTests(unittest.TestCase):
    def test_calibration_zip_is_stock_diffuse_only(self):
        zip_path = ROOT / "out" / "skins" / "calibration_stock_diffuse.zip"
        report_path = ROOT / "out" / "reports" / "calibration_stock_diffuse.json"
        preview_path = ROOT / "out" / "previews" / "calibration_stock_diffuse_projected_side_top_rear.png"

        self.assertTrue(zip_path.exists())
        self.assertTrue(report_path.exists())
        self.assertTrue(preview_path.exists())

        with zipfile.ZipFile(zip_path) as zf:
            self.assertEqual(set(zf.namelist()), {"Diffuse.dds", "Icon.dds"})
            self.assertEqual(
                {info.filename: info.date_time for info in zf.infolist()},
                {"Diffuse.dds": EXPECTED_ZIP_TIMESTAMP, "Icon.dds": EXPECTED_ZIP_TIMESTAMP},
            )
            diffuse = dds_info(zf.read("Diffuse.dds"))
            icon = dds_info(zf.read("Icon.dds"))

        self.assertEqual(diffuse["width"], 2048)
        self.assertEqual(diffuse["height"], 2048)
        self.assertEqual(diffuse["fourcc"], "DXT5")
        self.assertGreaterEqual(diffuse["mip_count"], 1)
        self.assertEqual(icon["fourcc"], "DXT5")

        report = json.loads(report_path.read_text())
        self.assertEqual(report["skin_name"], "calibration_stock_diffuse")
        self.assertEqual(report["package_files"], ["Diffuse.dds", "Icon.dds"])
        self.assertEqual(report["route"], "stock_diffuse_only")
        self.assertEqual(report["tmuf_smoke_test"], "not_run")
        self.assertEqual(report["evidence_status"]["gbuffer_mapping"], "experimental_until_tmuf_smoke")
        self.assert_report_records_stock_input_evidence(report)
        self.assert_report_records_output_artifacts(report)

    def assert_report_records_stock_input_evidence(self, report):
        manifest = json.loads((ROOT / "resources" / "evidence_manifest.json").read_text())
        manifest_by_path = {entry["path"]: entry for entry in manifest["resources"]}

        input_evidence = report["input_evidence"]
        expected_inputs = (
            EXPECTED_STOCK_INPUTS
            if report["skin_name"] == "calibration_stock_diffuse"
            else EXPECTED_PREMIUM_STOCK_INPUTS
        )
        self.assertEqual(set(input_evidence), set(expected_inputs))
        for path, expected_label in expected_inputs.items():
            self.assertEqual(input_evidence[path]["evidence_label"], expected_label)
            self.assertEqual(input_evidence[path]["sha256"], manifest_by_path[path]["sha256"])
            self.assertEqual(input_evidence[path]["size_bytes"], manifest_by_path[path]["size_bytes"])

    def assert_report_records_output_artifacts(self, report):
        output_artifacts = report["output_artifacts"]
        for key, pattern in EXPECTED_OUTPUT_ARTIFACTS.items():
            rel = pattern.format(name=report["skin_name"])
            path = ROOT / rel
            self.assertEqual(output_artifacts[key]["path"], rel)
            self.assertEqual(output_artifacts[key]["sha256"], sha256(path))
            self.assertEqual(output_artifacts[key]["size_bytes"], path.stat().st_size)


class PremiumStockBatchTests(unittest.TestCase):
    def test_premium_candidate_config_covers_twenty_mixed_archetypes(self):
        from src.stock_diffuse.premium import CANDIDATES, CANDIDATE_NAMES

        self.assertEqual(len(CANDIDATE_NAMES), 20)
        self.assertEqual(len(CANDIDATES), 20)
        self.assertEqual([candidate.name for candidate in CANDIDATES], CANDIDATE_NAMES)

        archetypes = [candidate.graphic_archetype for candidate in CANDIDATES]
        self.assertGreaterEqual(len(set(archetypes)), 12)
        self.assertIn("minimal_pinstripe", archetypes)
        self.assertIn("full_panel_dense", archetypes)
        self.assertIn("checker_tail", archetypes)
        self.assertIn("diagonal_sash", archetypes)
        self.assertIn("guard_halo", archetypes)

        minimal = next(candidate for candidate in CANDIDATES if candidate.graphic_archetype == "minimal_pinstripe")
        dense = next(candidate for candidate in CANDIDATES if candidate.graphic_archetype == "full_panel_dense")
        minimal_strengths = dict(minimal.mask_strengths)
        dense_strengths = dict(dense.mask_strengths)

        self.assertLess(minimal_strengths["side_blade"], 0.30)
        self.assertLess(minimal_strengths["rear_louvers"], 0.30)
        self.assertGreater(dense_strengths["side_blade"], 1.0)
        self.assertGreater(dense_strengths["rear_louvers"], 1.0)
        self.assertNotEqual(set(minimal.panel_catalog_targets), set(dense.panel_catalog_targets))

    def test_premium_batch_generates_stock_safe_experimental_candidates(self):
        from src.stock_diffuse.premium import CANDIDATE_NAMES, save_batch

        outputs = save_batch()
        self.assertEqual([item["name"] for item in outputs], CANDIDATE_NAMES)
        lane_ids = set()
        deeper_panel_masks = {
            "mid_deck_generated_panels",
            "mid_side_generated_panel",
            "nose_floor_generated_panels",
            "rear_floor_generated_panels",
            "rear_deck_fine_louver_rows",
        }

        for item in outputs:
            zip_path = Path(item["zip"])
            report_path = Path(item["report"])
            atlas_path = Path(item["atlas"])
            projection_path = Path(item["projection"])

            self.assertTrue(zip_path.exists(), zip_path)
            self.assertTrue(report_path.exists(), report_path)
            self.assertTrue(atlas_path.exists(), atlas_path)
            self.assertTrue(projection_path.exists(), projection_path)

            with zipfile.ZipFile(zip_path) as zf:
                self.assertEqual(set(zf.namelist()), {"Diffuse.dds", "Icon.dds"})
                self.assertEqual(
                    {info.filename: info.date_time for info in zf.infolist()},
                    {"Diffuse.dds": EXPECTED_ZIP_TIMESTAMP, "Icon.dds": EXPECTED_ZIP_TIMESTAMP},
                )
                diffuse = dds_info(zf.read("Diffuse.dds"))
                icon = dds_info(zf.read("Icon.dds"))

            self.assertEqual(diffuse["width"], 2048)
            self.assertEqual(diffuse["height"], 2048)
            self.assertEqual(diffuse["fourcc"], "DXT5")
            self.assertEqual(icon["fourcc"], "DXT5")

            report = json.loads(report_path.read_text())
            self.assertEqual(report["route"], "stock_diffuse_only")
            self.assertEqual(report["package_files"], ["Diffuse.dds", "Icon.dds"])
            self.assertEqual(report["tmuf_smoke_test"], "not_run")
            self.assertEqual(report["proof_gate"]["calibration_stock_diffuse"], "required_before_proven_use")
            self.assertEqual(report["evidence_status"]["gbuffer_mapping"], "experimental_until_tmuf_smoke")
            self.assertEqual(report["evidence_status"]["donor_gbx"], "not_used")
            self.assertNotIn("Details.dds", report["package_files"])
            self.assertNotIn("ProjShad.dds", report["package_files"])
            self.assertEqual(report["design_lane"]["evidence_status"], "recipe_metadata_not_tmuf_proof")
            self.assertIn("lane_id", report["design_lane"])
            self.assertIn("composition_focus", report["design_lane"])
            self.assertGreaterEqual(len(report["design_lane"]["distinctive_masks"]), 2)
            self.assertLessEqual(set(report["design_lane"]["distinctive_masks"]), set(report["masks_used"]))
            self.assertTrue(report["render_profile"]["lane_specific_strengths"])
            self.assertEqual(report["render_profile"]["evidence_status"], "recipe_metadata_not_tmuf_proof")
            self.assertIn("panel_family_strengths", report["render_profile"])
            self.assertGreaterEqual(
                len(deeper_panel_masks & set(report["render_profile"]["panel_family_strengths"])),
                1,
            )
            self.assertEqual(
                set(report["render_profile"]["distinctive_mask_strengths"]),
                set(report["design_lane"]["distinctive_masks"]),
            )
            self.assertEqual(set(report["mask_style_metrics"]), set(report["masks_used"]))
            self.assertGreaterEqual(len(deeper_panel_masks & set(report["masks_used"])), 1)
            accented_deeper_masks = [
                name
                for name in deeper_panel_masks & set(report["masks_used"])
                if report["mask_style_metrics"][name]["mean_alpha"] > 112
            ]
            self.assertGreaterEqual(len(accented_deeper_masks), 1)
            for mask_name in report["design_lane"]["distinctive_masks"]:
                self.assertGreaterEqual(
                    report["render_profile"]["distinctive_mask_strengths"][mask_name],
                    1.0,
                )
                self.assertGreater(report["mask_style_metrics"][mask_name]["mean_alpha"], 112)
            lane_ids.add(report["design_lane"]["lane_id"])
            self.assertGreaterEqual(report["style_metrics"]["dark_pixel_ratio"], 0.45)
            self.assertGreater(report["style_metrics"]["magenta_accent_ratio"], 0.005)
            self.assertGreater(report["style_metrics"]["cyan_accent_ratio"], 0.005)
            self.assertEqual(report["alpha_policy"]["route"], "conservative_dxt5_alpha")
            self.assertEqual(report["alpha_policy"]["material_effect_status"], "not_proven_until_tmuf_smoke")
            self.assertEqual(report["alpha_policy"]["tmuf_gloss_claim"], "none")
            self.assertGreaterEqual(report["alpha_metrics"]["min_alpha"], 100)
            self.assertLessEqual(report["alpha_metrics"]["max_alpha"], 155)
            self.assertIn(148, report["alpha_metrics"]["unique_alpha_values"])
            self.assertGreater(report["alpha_metrics"]["high_alpha_pixel_ratio"], 0.01)
            self.assertLess(report["alpha_metrics"]["high_alpha_pixel_ratio"], 0.45)
            self.assertIn("no_vignette", report["design_rules"])
            self.assertIn("no_random_scatter", report["design_rules"])
            self.assertIn("proven_local_panel_accents", report["design_rules"])
            self.assertIn("tailwing_bands", report["panel_catalog_targets"])
            self.assertIn("side_wings", report["panel_catalog_targets"])
            self.assertIn("mirrors_and_holders", report["panel_catalog_targets"])
            self.assertIn("underbody_dark", report["panel_catalog_targets"])
            self.assertEqual(
                report["design_lane"]["catalog_target_count"],
                len(report["panel_catalog_targets"]),
            )
            self.assertEqual(
                sorted(report["design_lane"]["primary_catalog_targets"]),
                sorted(report["panel_catalog_targets"]),
            )
            for local_mask in ("tailwing", "side_wings", "mirrors", "underplate", "main_body_under"):
                self.assertIn(local_mask, report["masks_used"])
                self.assertEqual(
                    report["mask_evidence"][local_mask]["evidence_status"],
                    "proven_local_psd_parts_label_map",
                )
            self.assertEqual(
                report["mask_evidence"]["mudguards"]["evidence_status"],
                "proven_local_psd_parts_label_map",
            )
            self.assertEqual(
                report["mask_evidence"]["center_spine"]["evidence_status"],
                "experimental_until_tmuf_smoke",
            )
            self.assertIn(
                "resources/authoritative/parts/psd_parts_labels.npy",
                report["mask_evidence"]["mudguards"]["source_files"],
            )
            CalibrationArtifactTests.assert_report_records_stock_input_evidence(self, report)
            CalibrationArtifactTests.assert_report_records_output_artifacts(self, report)

        self.assertEqual(len(lane_ids), len(CANDIDATE_NAMES))

        batch_index_path = ROOT / "out" / "reports" / "premium_batch_index.json"
        self.assertTrue(batch_index_path.exists())
        batch_index = json.loads(batch_index_path.read_text())
        self.assertEqual(batch_index["schema"], "tmuf_premium_skin_lab.premium_batch_index.v1")
        self.assertEqual(batch_index["route"], "stock_diffuse_only")
        self.assertTrue(batch_index["does_not_prove_tmuf_smoke"])
        self.assertEqual(batch_index["candidate_count"], len(CANDIDATE_NAMES))
        self.assertEqual([candidate["skin_name"] for candidate in batch_index["candidates"]], CANDIDATE_NAMES)
        self.assertEqual(
            len({candidate["design_lane"]["lane_id"] for candidate in batch_index["candidates"]}),
            len(CANDIDATE_NAMES),
        )
        for candidate in batch_index["candidates"]:
            self.assertEqual(candidate["tmuf_smoke_test"], "not_run")
            self.assertEqual(candidate["gbuffer_mapping"], "experimental_until_tmuf_smoke")
            self.assertEqual(candidate["package_files"], ["Diffuse.dds", "Icon.dds"])
            self.assertEqual(
                candidate["design_lane"]["catalog_target_count"],
                len(candidate["panel_catalog_targets"]),
            )
            self.assertTrue(candidate["render_profile"]["lane_specific_strengths"])
            self.assertEqual(
                set(candidate["render_profile"]["distinctive_mask_strengths"]),
                set(candidate["design_lane"]["distinctive_masks"]),
            )
            self.assertIn("skin_zip", candidate["output_artifacts"])
            self.assertIn("projected_preview", candidate["output_artifacts"])

        reports_by_name = {
            item["name"]: json.loads(Path(item["report"]).read_text())
            for item in outputs
        }
        self.assertIn("sidepod_blades", reports_by_name["black_magenta_cyan_blade"]["panel_catalog_targets"])
        self.assertIn("nose_side_generated_panels", reports_by_name["black_magenta_cyan_blade"]["panel_catalog_targets"])
        self.assertIn("nose_deck_generated_panels", reports_by_name["black_magenta_cyan_blade"]["panel_catalog_targets"])
        self.assertIn("center_spine", reports_by_name["black_cyan_spine"]["panel_catalog_targets"])
        self.assertIn("rear_deck_fine_louver_rows", reports_by_name["dark_neon_louver"]["panel_catalog_targets"])
        self.assertIn("engine_rear_deck", reports_by_name["dark_neon_louver"]["panel_catalog_targets"])
        self.assertIn("front_mudguard_caps", reports_by_name["violet_cyber_flow"]["panel_catalog_targets"])
        self.assertIn("rear_mudguard_caps", reports_by_name["violet_cyber_flow"]["panel_catalog_targets"])
        self.assertGreater(
            reports_by_name["dark_neon_louver"]["render_profile"]["mask_strengths"]["rear_louvers"],
            reports_by_name["dark_neon_louver"]["render_profile"]["mask_strengths"]["side_blade"],
        )
        self.assertGreater(
            reports_by_name["black_magenta_cyan_blade"]["render_profile"]["mask_strengths"]["side_blade"],
            reports_by_name["black_magenta_cyan_blade"]["render_profile"]["mask_strengths"]["rear_louvers"],
        )
        self.assertGreater(
            reports_by_name["black_cyan_spine"]["render_profile"]["mask_strengths"]["center_spine"],
            reports_by_name["black_cyan_spine"]["render_profile"]["mask_strengths"]["side_blade"],
        )


if __name__ == "__main__":
    unittest.main()
