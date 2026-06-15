# TMUF Premium Skin Lab

Clean, isolated workspace for evidence-backed TMUF/TMNF StadiumCar skin generation.

## Goal

Generate polished premium StadiumCar skins, starting with stock-safe
`Diffuse.dds` + `Icon.dds` packages. The target is a lane-based generator:
minimal black/red, black/gold precision, two-tone prototype, flow stripes,
technical panel maps, abstract art-car designs, op-art speed fields, and dark
neon prototypes. No lane may rely on donor or StadiumCar V2 UV assumptions.

## Core Rule

Nothing in this project is treated as true unless it has an evidence label:

- `proven`: verified by local files, local research docs, or direct source identity.
- `reference_only`: useful visually or historically, but not authoritative.
- `experimental`: usable only behind a proof gate.
- `rejected`: known wrong for the TMUF/TMNF StadiumCar target.

The generated ledger is:

`resources/evidence_manifest.json`

Regenerate it with:

```bash
python3 -m src.evidence.build_manifest
```

The generated stock panel inventory is:

`out/reports/stock_part_inventory.json`

Regenerate it with:

```bash
python3 recipes/explore_stock_parts.py
```

See `docs/panel_geometry_livery_plan.md` for the current panel map, livery
research lanes, and proof gates.

## Current Milestone

The first proof artifact is the stock Diffuse calibration skin:

```text
out/skins/calibration_stock_diffuse.zip
out/previews/calibration_stock_diffuse_atlas.png
out/previews/calibration_stock_diffuse_projected_side_top_rear.png
out/reports/calibration_stock_diffuse.json
```

This package intentionally contains only:

```text
Diffuse.dds
Icon.dds
```

Its purpose is to prove whether the copied GBuffer and stock template align in
TMUF. Until that smoke test is done, GBuffer-driven painting stays
`experimental`.

The first premium stock-safe batch is also generated:

```text
out/skins/black_magenta_cyan_blade.zip
out/skins/black_cyan_spine.zip
out/skins/violet_cyber_flow.zip
out/skins/dark_neon_louver.zip
out/skins/magenta_cyan_race_proto.zip
```

Those skins intentionally remain behind the same calibration proof gate.

## Run

```bash
python3 recipes/stock_calibration.py
python3 recipes/stock_premium_neon.py
python3 recipes/explore_stock_parts.py
python3 recipes/tmuf_smoke_gate.py --write-template
python3 recipes/prepare_tmuf_smoke_kit.py
python3 recipes/find_tmuf_skin_dirs.py --write
python3 recipes/validate_stock_outputs.py
python3 recipes/validate_profile_gates.py
python3 recipes/lab_status.py --write
python3 -m unittest discover -s tests
```

See `docs/tmuf_smoke_test.md` before promoting any report from
`experimental_until_tmuf_smoke` to `proven_by_tmuf_smoke`.

After the calibration skin is loaded in TMUF/TMNF, record the real screenshots
and explicit observation confirmation with:

```bash
python3 recipes/record_tmuf_smoke.py --tester "manual tester" --tmuf-build "TMUF local install" --test-date-local 2026-06-15 --screenshot /path/to/tmuf_calibration.png --confirm-observation nose_is_red --confirm-observation tail_is_blue --confirm-observation left_side_is_green --confirm-observation right_side_is_yellow --confirm-observation roof_high_surfaces_are_white --confirm-observation lower_floor_surfaces_are_dark --confirm-observation mudguards_are_magenta --confirm-observation centerline_is_cyan --confirm-observation package_loads_without_custom_gbx
python3 recipes/tmuf_smoke_gate.py --evaluate out/proof/calibration_tmuf_smoke.json
```
