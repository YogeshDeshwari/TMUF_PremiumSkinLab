# Validation Checklist

Use this before calling any skin complete.

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
- [ ] No `reference_only` input is treated as stock truth.
- [ ] No `experimental` feature is enabled without a proof report.
- [ ] Any TMUF/game behavior claim has a smoke-test note.

## Visual Checks

- [ ] Atlas preview exists.
- [ ] Projected side/top/rear preview exists.
- [ ] Broad graphics are readable.
- [ ] Accent colors are not random scatter.
- [ ] Mudguard and wheel treatment matches the route being tested.

## TMUF Smoke Check

- [ ] Confirm the validator reports `tmuf_smoke_status=pending` before manual
      TMUF evidence exists.
- [ ] Put zip into the StadiumCar skin folder.
- [ ] Load the skin in TMUF.
- [ ] Capture at least front, side, rear, and top-ish views.
- [ ] Update the report JSON from `tmuf_smoke_test: not_run` to the actual result.
- [ ] Promote or keep evidence status based on the result.
