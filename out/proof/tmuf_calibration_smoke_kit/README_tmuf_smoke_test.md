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
calibration preview, the supplemental panel-family probe, and current premium
candidates. The kit is only a handoff bundle. It does not prove TMUF smoke
status.

The kit also includes:

```text
skins/calibration_panel_family_probe.zip
reports/calibration_panel_family_probe.json
previews/calibration_panel_family_probe_atlas.png
previews/calibration_panel_family_probe_projected_side_top_rear.png
```

This probe colors the audited front/nose, cockpit/deck, side/flank, rear/tail,
and support families using the local catalog evidence, with bright overlays for
generator-only masks such as `nose_spear`, `side_blade`, `rear_louvers`,
`rear_center_glow`, and `tail_bar`. It is stock Diffuse-only, but it is
supplemental. It helps inspect panel-family runtime visibility and does not
replace `calibration_stock_diffuse.zip` as the gate artifact.

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

To summarize the current setup state and get the next exact command, write the
readiness report:

```bash
python3 recipes/smoke_readiness.py --write --write-command-packet
```

This writes:

```text
out/proof/tmuf_smoke_readiness.json
out/proof/tmuf_manual_smoke_commands.txt
```

The readiness report does not prove TMUF smoke status. It only reports whether
the local kit is fresh, how many StadiumCar folders were found, whether an
install receipt exists, and which command should be run next. The command
packet is the same setup guidance in copy-friendly text form.

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
  --install-receipt out/proof/tmuf_calibration_smoke_kit/proof/calibration_install_receipt.json \
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

When `--install-receipt` is provided, the helper copies that receipt into
`out/proof/calibration_install_receipt.json` and records the receipt hash plus
the installed calibration zip hash. Later smoke evaluation fails if the receipt
or copied calibration zip no longer matches the recorded evidence.

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

Preview exactly which reports would be promoted:

```bash
python3 recipes/tmuf_smoke_gate.py --apply out/proof/calibration_tmuf_smoke.json --dry-run
```

The dry run prints JSON with `would_update` and `would_skip` lists. It does
not write any report files.

To test the post-smoke promotion and validation pipeline without writing fake
proof into the real project, run a synthetic self-test in a scratch workspace:

```bash
python3 recipes/synthetic_post_smoke_selftest.py \
  --workspace /tmp/tmuf_premium_synthetic_post_smoke \
  --json
```

This copies the current reports, skins, previews, and evidence manifest into
the scratch workspace, generates synthetic nonblank screenshots there, applies
the smoke promotion only inside that copy, and then runs stock/profile
validators against the copy. It must report `synthetic_smoke=true` and
`claims_real_tmuf_proof=false`. This command proves the promotion code path
works; it does not prove that TMUF/TMNF loaded the calibration skin.
If the workspace path already exists, the command removes it only when it
contains the synthetic self-test marker file. It refuses unmarked existing
paths so an arbitrary directory is not deleted by accident.

Only after it evaluates as passed, promote generated reports:

```bash
python3 recipes/tmuf_smoke_gate.py --apply out/proof/calibration_tmuf_smoke.json
```

This updates report-level GBuffer status and GBuffer-derived `mask_evidence`
entries from:

```text
experimental_until_tmuf_smoke
mixed_generated_labels_and_experimental_gbuffer
mixed_local_label_and_experimental_gbuffer
```

to:

```text
proven_by_tmuf_smoke
```

The apply step promotes only stock skin reports and
`premium_batch_index.json`. It skips inventory, deep-dive, lab-status, and
other non-skin evidence JSON files. It also skips supplemental smoke artifacts
such as `calibration_panel_family_probe.json`; those probe files are visual
inspection aids, not gate-passing reports. The premium batch index is updated
to carry the same smoke evidence and `tmuf_smoke_status=passed`.
Stock validation does not trust those promoted fields by themselves: it
re-evaluates the referenced smoke report and its screenshot fingerprints before
counting any skin as smoke-passed.

Do not apply this gate from projected previews alone.

To copy the calibration skin into an explicit StadiumCar skin folder:

```bash
python3 recipes/prepare_tmuf_smoke_kit.py --install-skins-dir /path/to/StadiumCar
```

The install target must already exist and match a recognized StadiumCar skin
route such as `Skins/Vehicles/StadiumCar`. The install helper only copies
`calibration_stock_diffuse.zip`; it does not promote reports or mark the smoke
gate as passed.

If discovery finds exactly one recognized StadiumCar skin folder, the helper can
install there without copying the path manually:

```bash
python3 recipes/prepare_tmuf_smoke_kit.py --install-discovered
```

To limit discovery to a known parent folder, pass one or more search roots:

```bash
python3 recipes/prepare_tmuf_smoke_kit.py \
  --install-discovered \
  --search-root /path/to/TrackMania-or-Wine-prefix
```

This route refuses to install when discovery finds zero candidates or multiple
candidates. The install receipt records `selection_mode`,
`selected_candidate`, and the discovery audit. Finding one directory still does
not prove TMUF smoke status; it only proves which folder received the copied
calibration zip.

To also install the supplemental panel-family probe in the same StadiumCar skin
folder, opt in explicitly:

```bash
python3 recipes/prepare_tmuf_smoke_kit.py \
  --install-skins-dir /path/to/StadiumCar \
  --install-panel-probe
```

This copies both `calibration_stock_diffuse.zip` and
`calibration_panel_family_probe.zip`. The probe is still supplemental: its
install receipt records it as `does_not_prove_tmuf_smoke=true`, and the smoke
gate apply step skips its report.

When `--install-skins-dir` or `--install-discovered` is used, the helper also
writes:

```text
out/proof/tmuf_calibration_smoke_kit/proof/calibration_install_receipt.json
```

That receipt records the copied zip path, route, SHA256, and next required
evidence. It still has `does_not_prove_tmuf_smoke=true`.
