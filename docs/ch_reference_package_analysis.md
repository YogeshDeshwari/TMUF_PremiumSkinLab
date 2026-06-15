# CH Reference Package Analysis

Generated reports:

- `out/reference_analysis/CH_Blu_report.json`
- `out/reference_analysis/CH_Bloom_Wheel_LED_Underglow_report.json`
- `out/reference_analysis/reference_package_index.json`

Generated contact sheets:

- `out/reference_analysis/CH_Blu_contact_sheet.png`
- `out/reference_analysis/CH_Bloom_Wheel_LED_Underglow_contact_sheet.png`

## Evidence Boundary

Both packages are `custom_fullcar_ch2026_reference`, not stock Diffuse-only
packages. They include:

- `Diffuse.dds`
- `Details.dds`
- `Icon.dds`
- `ProjShad.dds`
- `MainBody.Solid.Gbx`
- `MainBodyHigh.Solid.Gbx`
- `DiffuseDirty.dds`
- `DetailsDirty.dds`
- `skin.json`

Both packages have `MainBody.Solid.Gbx` and `MainBodyHigh.Solid.Gbx` hashes that
match `resources/experimental/base_car/CH_2026_NOT_STOCK_STADIUM_DETAILS_CUSTOM_MESH.zip`.

That makes them valid CH_2026 full-car references and invalid as stock
StadiumCar Diffuse-only truth.

## Visual Takeaways

`CH_Blu.zip`:

- Theme: `CH_TronBlue_L123_v2`.
- Finish: `CHROME`, `finish_alpha=255`.
- Diffuse is radial blue energy-line composition.
- Details carries blue wheel/detail accents.
- ProjShad carries blue underglow.

`CH_Bloom_Wheel_LED_Underglow.zip`:

- Theme: `CH_Cyber_SynthwaveGrid_WheelFix_LED_Underglow`.
- Finish: `GLOSS`, `finish_alpha=127`.
- Diffuse is dense magenta/cyan speckle-grid composition.
- Details carries purple wheel/detail accents.
- ProjShad carries magenta underglow.

## Use In The Lab

Use these only for the later CH_2026 full-car lane:

- wheel LED and detail-map composition reference,
- ProjShad underglow reference,
- full package file-route reference,
- texture contrast/style reference.

Do not use them to prove stock StadiumCar UVs, stock GBuffer mapping, tyre
routing, or stock Diffuse-only behavior.
