# Master Plan

## Objective

Build a clean premium TMUF/TMNF StadiumCar skin generator in this folder:

`/Users/ydeshwari/Documents/TMUF_PremiumSkinLab`

The new project must not import from `TM_CARS` or `tmuf_liveries` at runtime.
Those folders are evidence/reference libraries only.

## Phase 1: Evidence Locker

Create and maintain:

```text
resources/authoritative/
resources/reference_only/
resources/experimental/
resources/evidence_manifest.json
```

Every copied file must have:

- SHA256
- size
- dimensions or DDS metadata when available
- evidence label
- safe use
- limits

## Phase 2: Stock Calibration

Generate:

```text
out/skins/calibration_stock_diffuse.zip
```

The package contains only:

```text
Diffuse.dds
Icon.dds
```

Calibration colors:

- nose: red
- tail: blue
- left: green
- right: yellow
- high/roof: white
- lower/floor: dark
- mudguards: magenta
- centerline: cyan

Pass condition:

- The car loads in TMUF.
- Colors appear on the intended regions.
- No custom GBX, `Details.dds`, or `ProjShad.dds` is needed.

## Phase 3: Premium Stock Diffuse Generator

After calibration passes, build the first real generator:

```text
src/stock_diffuse/
recipes/stock_premium_neon.py
```

Output per skin:

```text
out/skins/<name>.zip
out/previews/<name>_atlas.png
out/previews/<name>_projected_side_top_rear.png
out/reports/<name>.json
```

Rules:

- Use GBuffer for 3D placement.
- Use `psd_parts` for footprint and mudguard masks.
- Use AO/prelight for depth.
- Rewrite old motif ideas cleanly.
- Do not use StadiumCar V2 UVs.
- Do not use donor GBX.
- Do not ship `Details.dds` or `ProjShad.dds` in this lane.

First candidate names:

- `black_magenta_cyan_blade`
- `black_cyan_spine`
- `violet_cyber_flow`
- `dark_neon_louver`
- `magenta_cyan_race_proto`

## Phase 4: CH_2026 Full-Car Lane

Only after stock Diffuse skins look good.

Profile:

```text
src/profiles/ch2026_fullcar/
```

Input:

```text
resources/experimental/base_car/CH_2026_NOT_STOCK_STADIUM_DETAILS_CUSTOM_MESH.zip
```

Allowed features:

- controlled `Details.dds`
- wheel disc LED rings
- tyre sidewall/tread fill
- pass-through dirty maps
- optional `ProjShad.dds` underglow
- full package with GBX files

Rule:

Wheel and tyre coordinates are CH_2026 profile data, not global truth.

## Phase 5: No-Mudguard Lane

Only after the CH_2026 full-car lane works.

Profile:

```text
src/profiles/ch2026_nomud/
```

Tool:

```bash
dotnet resources/experimental/flows/remove_guards/bin/Release/net9.0/remove_guards.dll input.Solid.Gbx output.Solid.Gbx
```

Known current evidence:

- high mesh removes 6 named objects
- low mesh removes 0 named objects

Therefore no-mudguard remains experimental until packaged and smoke-tested in
TMUF.

