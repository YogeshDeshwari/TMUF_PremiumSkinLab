# TMUF Calibration Smoke Test

This project does not treat GBuffer-driven placement as proven until the
calibration skin is loaded in TMUF/TMNF and checked against the required
regions.

## Artifact

Install or load:

```text
out/skins/calibration_stock_diffuse.zip
```

The package must contain only:

```text
Diffuse.dds
Icon.dds
```

## Required Observations

All observations must be true before the gate can pass:

- nose is red
- tail is blue
- left side is green
- right side is yellow
- roof/high surfaces are white
- lower/floor surfaces are dark
- mudguards are magenta
- centerline is cyan
- package loads without custom GBX files

At least one screenshot path must be recorded and the screenshot file must
exist locally.

## Workflow

Create the template:

```bash
python3 recipes/tmuf_smoke_gate.py --write-template
```

Fill this file after the TMUF test:

```text
out/proof/calibration_tmuf_smoke_template.json
```

Save the filled copy as:

```text
out/proof/calibration_tmuf_smoke.json
```

Evaluate it without changing generated reports:

```bash
python3 recipes/tmuf_smoke_gate.py --evaluate out/proof/calibration_tmuf_smoke.json
```

Only after it evaluates as passed, promote generated reports:

```bash
python3 recipes/tmuf_smoke_gate.py --apply out/proof/calibration_tmuf_smoke.json
```

This updates reports from:

```text
experimental_until_tmuf_smoke
```

to:

```text
proven_by_tmuf_smoke
```

Do not apply this gate from projected previews alone.
