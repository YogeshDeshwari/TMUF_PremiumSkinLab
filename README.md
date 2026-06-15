# TMUF Premium Skin Lab

Clean, isolated workspace for evidence-backed TMUF/TMNF StadiumCar skin generation.

## Goal

Generate polished premium StadiumCar skins, starting with stock-safe
`Diffuse.dds` + `Icon.dds` packages. The first target style is a dark
black/charcoal car with magenta and cyan accents, broad readable graphics, and
no donor or StadiumCar V2 UV assumptions.

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

## Current Milestone

The first artifact is the stock Diffuse calibration skin:

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

## Run

```bash
python3 recipes/stock_calibration.py
python3 -m unittest discover -s tests
```

