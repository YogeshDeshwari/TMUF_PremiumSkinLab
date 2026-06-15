# Validation Checklist

Use this before calling any skin complete.

## Status Check

- [ ] Run `python3 recipes/lab_status.py --write`.
- [ ] Confirm `objective_status` is not `complete` unless TMUF smoke evidence
      has passed.

## Package Checks

- [ ] Run `python3 recipes/validate_stock_outputs.py`.
- [ ] Zip opens.
- [ ] Stock Diffuse lane contains only `Diffuse.dds` and `Icon.dds`.
- [ ] Full-car lane contains expected GBX, `Diffuse.dds`, `Details.dds`,
      `Icon.dds`, and optional auxiliary textures.
- [ ] DDS headers match expected dimensions and formats.
- [ ] No `__MACOSX`, `.DS_Store`, or AppleDouble files.
- [ ] Report JSON exists.

## Evidence Checks

- [ ] Every input exists in `resources/evidence_manifest.json`.
- [ ] Run `python3 recipes/explore_stock_parts.py`.
- [ ] Confirm `out/reports/stock_part_inventory.json` reports 41 `psd_parts`
      zones, 60 `panels_high` zones, and 107 `panels_fine` zones.
- [ ] No `reference_only` input is treated as stock truth.
- [ ] No `experimental` feature is enabled without a proof report.
- [ ] Any TMUF/game behavior claim has a smoke-test note.
- [ ] Premium candidate reports include `mask_evidence` for every `masks_used`
      entry.
- [ ] Locally named PSD masks stay labeled as local proof.
- [ ] GBuffer-derived masks stay `experimental_until_tmuf_smoke` before smoke
      proof and become `proven_by_tmuf_smoke` only after the smoke gate applies
      passed TMUF evidence.
- [ ] Premium reports include `alpha_policy` and `alpha_metrics`, with
      `tmuf_gloss_claim=none` until TMUF material behavior is smoke-tested.
- [ ] Premium reports include distinct `design_lane` metadata, and the lane
      `evidence_status` remains `recipe_metadata_not_tmuf_proof`.
- [ ] Premium reports include `panel_catalog_targets`, and every target exists
      in `out/reports/stock_part_inventory.json`.
- [ ] `design_lane.primary_catalog_targets` and `catalog_target_count` match
      each report's `panel_catalog_targets`.
- [ ] Premium reports include `render_profile` and `mask_style_metrics`, and
      distinctive masks have recorded lane-specific strengths.
- [ ] `out/reports/premium_batch_index.json` matches the individual premium
      reports and keeps `does_not_prove_tmuf_smoke=true`.
- [ ] Run `python3 recipes/validate_profile_gates.py` before touching CH_2026
      full-car or no-mudguard lanes.

## Visual Checks

- [ ] Validator reports `preview_visual_quality_passed=True`.
- [ ] Premium candidates report `premium_style_quality_passed=True`.
- [ ] Atlas preview exists.
- [ ] Projected side/top/rear preview exists.
- [ ] Broad graphics are readable.
- [ ] Accent colors are not random scatter.
- [ ] Mudguard and wheel treatment matches the route being tested.

## TMUF Smoke Check

- [ ] Confirm the validator reports `tmuf_smoke_status=pending` before manual
      TMUF evidence exists.
- [ ] Put zip into the StadiumCar skin folder using either an explicit
      `--install-skins-dir` target or guarded `--install-discovered` with one
      candidate.
- [ ] Load the skin in TMUF.
- [ ] Capture role-labeled `front`, `side`, `rear`, and `top` views.
- [ ] Record evidence with `python3 recipes/record_tmuf_smoke.py ... --install-receipt ... --screenshot-role front=... --screenshot-role side=... --screenshot-role rear=... --screenshot-role top=...`.
- [ ] Confirm smoke evaluation reports no missing, invalid, or mismatched install
      receipt evidence before applying the gate.
- [ ] Evaluate with `python3 recipes/tmuf_smoke_gate.py --evaluate out/proof/calibration_tmuf_smoke.json`.
- [ ] Promote with `python3 recipes/tmuf_smoke_gate.py --apply out/proof/calibration_tmuf_smoke.json`
      only if the evaluation passes.

## Custom Profile Gates

- [ ] `ch2026_fullcar` remains locked until stock calibration smoke passes.
- [ ] `ch2026_nomud` remains locked until CH_2026 full-car smoke passes.
- [ ] CH_2026 donor zip is treated as `experimental`, not stock truth.
- [ ] `remove_guards` evidence remains CH_2026-specific and experimental.
