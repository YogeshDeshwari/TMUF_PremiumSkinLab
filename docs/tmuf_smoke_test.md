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

At least one screenshot path must be recorded. Each referenced screenshot must
exist locally, open as an image, contain nonblank visual content, and match the
fingerprint recorded in the smoke evidence file.

## Workflow

Create a smoke-test kit:

```bash
python3 recipes/prepare_tmuf_smoke_kit.py
```

This writes:

```text
out/proof/tmuf_calibration_smoke_kit/
out/proof/tmuf_calibration_smoke_kit.zip
```

The kit is only a handoff bundle. It does not prove TMUF smoke status.

Create the template if you want a manual form:

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

Preferred path: record the real smoke evidence with the helper after the skin
has been loaded in TMUF/TMNF and the required observations have been checked:

```bash
python3 recipes/record_tmuf_smoke.py \
  --tester "manual tester" \
  --tmuf-build "TMUF local install" \
  --test-date-local 2026-06-15 \
  --screenshot /path/to/tmuf_calibration_front.png \
  --screenshot /path/to/tmuf_calibration_side.png \
  --all-required-observations-passed
```

The helper copies screenshots into:

```text
out/proof/tmuf_smoke_screenshots/
```

The helper rejects missing files, unreadable image files, and single-color blank
images before it writes the evidence report. It also records each screenshot's
SHA256, byte size, width, and height so later evaluation can detect changed
proof files.

and writes:

```text
out/proof/calibration_tmuf_smoke.json
```

It does not promote generated reports. It only records a filled evidence file
that the smoke gate can evaluate.

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

To copy the calibration skin into an explicit StadiumCar skin folder:

```bash
python3 recipes/prepare_tmuf_smoke_kit.py --install-skins-dir /path/to/StadiumCar
```

The install helper only copies `calibration_stock_diffuse.zip`; it does not
promote reports or mark the smoke gate as passed.
