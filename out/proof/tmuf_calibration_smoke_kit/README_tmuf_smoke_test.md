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

Four role-labeled screenshot paths must be recorded: `front`, `side`, `rear`,
and `top`. Each referenced screenshot must exist locally, open as an image,
contain nonblank visual content, and match the fingerprint recorded in the smoke
evidence file.

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

The kit includes the calibration skin, smoke report template,
`proof/tmuf_smoke_run_manifest.json`, calibration previews, and
`previews/tmuf_smoke_contact_sheet.png`, a visual review sheet for the
calibration preview and current premium candidates. The kit is only a handoff
bundle. It does not prove TMUF smoke status.

Find existing StadiumCar skin directories before installing:

```bash
python3 recipes/find_tmuf_skin_dirs.py --write
```

This writes:

```text
out/proof/tmuf_skin_dirs.json
```

Finding a directory does not prove TMUF smoke status. It only identifies an
explicit candidate target for the install helper.

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
  --screenshot-role front=/path/to/tmuf_calibration_front.png \
  --screenshot-role side=/path/to/tmuf_calibration_side.png \
  --screenshot-role rear=/path/to/tmuf_calibration_rear.png \
  --screenshot-role top=/path/to/tmuf_calibration_top.png \
  --confirm-observation nose_is_red \
  --confirm-observation tail_is_blue \
  --confirm-observation left_side_is_green \
  --confirm-observation right_side_is_yellow \
  --confirm-observation roof_high_surfaces_are_white \
  --confirm-observation lower_floor_surfaces_are_dark \
  --confirm-observation mudguards_are_magenta \
  --confirm-observation centerline_is_cyan \
  --confirm-observation package_loads_without_custom_gbx
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

The run manifest in the smoke kit is machine-readable checklist data. It
records the required screenshot roles, required observations, command
templates, and current install-directory discovery status. It is not evidence
that TMUF loaded the package.

Evaluate it without changing generated reports:

```bash
python3 recipes/tmuf_smoke_gate.py --evaluate out/proof/calibration_tmuf_smoke.json
```

Only after it evaluates as passed, promote generated reports:

```bash
python3 recipes/tmuf_smoke_gate.py --apply out/proof/calibration_tmuf_smoke.json
```

This updates report-level GBuffer status and GBuffer-derived `mask_evidence`
entries from:

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

The install target must already exist and match a recognized StadiumCar skin
route such as `Skins/Vehicles/StadiumCar`. The install helper only copies
`calibration_stock_diffuse.zip`; it does not promote reports or mark the smoke
gate as passed.

When `--install-skins-dir` is used, the helper also writes:

```text
out/proof/tmuf_calibration_smoke_kit/proof/calibration_install_receipt.json
```

That receipt records the copied zip path, route, SHA256, and next required
evidence. It still has `does_not_prove_tmuf_smoke=true`.
