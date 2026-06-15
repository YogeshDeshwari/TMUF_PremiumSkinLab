# Panel Geometry And Livery Plan

This document is the working evidence map for deeper StadiumCar skin design. It
does not make TMUF runtime claims. A panel, mask, or design lane is treated as
production truth only after the relevant proof gate passes.

## Evidence Boundaries

Local evidence:

- `resources/authoritative/parts/psd_parts.json`: 41 named PSD zones, backed by
  `psd_parts_labels.npy`.
- `resources/authoritative/parts/panels_high.json`: 60 generated panel zones,
  backed by `panels_high_labels.npy`.
- `resources/authoritative/parts/panels_fine.json`: 107 generated panel zones,
  backed by `panels_fine_labels.npy`.
- `resources/authoritative/mesh/*.obj`: 13 local mesh exports. Every OBJ has
  vertices, UVs, normals, and faces; every face references UVs.
- `resources/authoritative/gbuffer/*`: coverage, normal, and position buffers.
  These are strong local projection evidence, but remain
  `experimental_until_tmuf_smoke`.
- `out/reports/stock_part_inventory.json`: generated inventory report from
  `recipes/explore_stock_parts.py`.

Reference-only web/design evidence:

- [Honda MP4/4](https://global.honda/en/F1/machine/1988_McLarenHondaMP44/):
  low, narrow, dominant 1988 F1 geometry; useful for long, clean nose-to-tail
  composition, not for copying tobacco branding.
- [Classic Team Lotus JPS](https://classicteamlotus.co.uk/en/news/posts/2019/black-gold-the-story-of-the-john-player-specials/):
  black/gold livery history; useful for black base plus thin metallic trim,
  not for copying JPS marks.
- [Porsche Pink Pig](https://www.porsche.com/stories/innovation/what-is-the-porsche-pink-pig/):
  contour/panel annotation livery; useful for technical panel-line concepts.
- [Gulf livery](https://www.gulfoilltd.com/gulf-livery): iconic orange/blue
  two-color motorsport system; useful for broad two-color contrast grammar.
- [MARTINI Racing](https://www.martini.com/racing/): blue, light blue, and red
  stripe identity; useful for parallel stripe systems.
- [BMW Art Cars](https://www.bmwgroup.com/en/sustainability/society/bmw-art-cars.html):
  racing cars as artist-designed objects; useful for abstract, pop, geometric,
  and gestural lanes.
- [Tate abstract art](https://www.tate.org.uk/art/art-terms/a/abstract-art)
  and [Tate Op art](https://www.tate.org.uk/art/art-terms/o/op-art): useful
  for shape/color/form/mark and geometric optical-effect grammar.
- [MoMA geometric abstraction](https://www.moma.org/collection/terms/geometric-abstraction):
  useful as a reference set for geometric abstraction vocabulary.

Rejected as stock truth:

- Brand logos, trade dress, or text marks from Marlboro, JPS, Gulf, Martini, or
  other real teams.
- StadiumCar V2 UVs as stock StadiumCar mapping.
- CH_2026 donor GBX assumptions in the stock Diffuse lane.
- `Details.dds`, `ProjShad.dds`, wheel/tyre full-car work, or no-mudguard work
  in the stock Diffuse lane.

## Atlas Evidence

All three label maps are `2048x2048` `int32`, and every JSON zone id matches
the corresponding `.npy` labels.

| Map | Zones | Atlas coverage | Evidence use |
| --- | ---: | ---: | --- |
| `psd_parts` | 41 | 97.8331% | Named zones; safest basis for explicit panel ownership. |
| `panels_high` | 60 | 97.5965% | Larger generated segmentation; useful for extra panels after probe. |
| `panels_fine` | 107 | 97.5965% | Fine segmentation; use for detail accents and panel probes, not hero shapes by default. |

Risk classes used by `out/reports/stock_part_inventory.json`:

- `broad_design_surface`: area `>= 100000`; safe for large fields, stripes, and
  identity shapes by atlas footprint.
- `medium_accent_surface`: area `25000..99999`; safe for accent blocks, bands,
  trim, and secondary color.
- `small_detail_surface`: area `5000..24999`; use for subtle highlights,
  vents, mirrors, holders, and small linework.
- `probe_only_tiny_fragment`: area `< 5000`; do not use for premium hero
  design until a probe confirms visibility.

`out/reports/stock_part_inventory.json` also includes
`paintable_panel_catalog`, the machine-readable panel targeting catalogue for
the stock Diffuse lane. It separates local label-map panels from mixed
local-plus-GBuffer panels and GBuffer-only geometry panels. Every catalog entry
keeps `tmuf_runtime_status=not_proven_until_smoke`; it is evidence for atlas
targeting, not proof of in-game visibility.

## Named PSD Surface Families

`psd_parts` is the primary named map.

| Family | Zones | Total area | Primary use |
| --- | ---: | ---: | --- |
| `main_body_top` | 4 | 1,622,702 | Main base fields, center spines, large diagonals, abstract blocks. |
| `helmet` | 4 | 539,541 | Optional pilot color continuity; do not overdrive main livery from helmet. |
| `mudguards` | 9 | 425,340 | Front/rear caps, colored rims, guard-edge pinlines. |
| `main_body_under` | 4 | 353,313 | Low/underbody dark material, subtle accent returns. |
| `side_under_color` | 2 | 263,234 | Sidepod/lower side color blades and sponsor-like blocks without text. |
| `tailwing` | 3 | 177,929 | Wing bands, edge trim, high contrast rear signature. |
| `licence_plate` | 2 | 143,240 | Usually low priority; can hold abstract plaque blocks, no real sponsor text. |
| `underplate` | 3 | 136,321 | Dark underside and low reflective fields. |
| `side_wings` | 2 | 125,401 | Winglets and side aero accents. |
| `nose` | 1 | 101,934 | Front identity spear, wedge tip, number-free badge field. |
| `helmet_glass` | 2 | 82,557 | Visor/glass shade; keep restrained. |
| `wheel_blocks` | 2 | 64,829 | Stock Diffuse only: treat as uncertain visible blocks, not real tyre/wheel truth. |
| `mirrors` | 2 | 47,755 | Small contrast flicks and left/right color checks. |
| `BigSideVentOneInSideColor` | 1 | 19,322 | Small vent accent only. |

Broad-safe individual `psd_parts` zones:

- `MainBodyTOP_BR`: area `428023`, bbox `[993,1448,1976,2047]`.
- `MainBodyTOP_TR`: area `420656`, bbox `[993,844,1961,1447]`.
- `MainBodyTOP_BL`: area `395442`, bbox `[237,1445,992,2047]`.
- `MainBodyTOP_TL`: area `378581`, bbox `[236,885,992,1449]`.
- `Helmet_BR`, `Helmet_TL`, `Helmet_BL`, `Helmet_TR`: all above `133000`.
- `SideUnderColor_R`: area `136322`, bbox `[120,864,324,2047]`.
- `SideUnderColor_L`: area `126912`, bbox `[0,842,174,2047]`.
- `MainBodyUNDER_TR`: area `105320`.
- `NosePart`: area `101934`, bbox `[1575,1238,2047,1655]`.

Small-detail examples:

- `MirrorHolders`: area `19930`, bbox `[0,1268,76,1601]`.
- `BigSideVentOneInSideColor`: area `19322`.
- `KNob.Gouing.inside.Rear.wheel`: area `18735`.

## Generated Panel Families

`panels_high` and `panels_fine` are useful because they divide the body into
many more surfaces, but their names are generated. Their names support only the
tokens they contain: `nose`, `mid`, `rear`, `deck`, `floor`, and `side`.

`panels_high` group totals:

- `nose_*`: 12 zones, total area `1456561`.
- `mid_*`: 9 zones, total area `1418110`.
- `rear_*`: 39 zones, total area `1218824`.

Broad-safe `panels_high` examples:

- `nose_side_C_04`: area `1020619`.
- `mid_side_C_02`: area `623575`.
- `mid_deck_C_79`: area `489506`.
- `rear_floor_C_15`: area `188329`.
- `nose_floor_C_66`: area `132067`.
- `rear_deck_C_63`: area `125470`.
- `rear_deck_C_08`: area `117867`.
- `mid_deck_C_48`: area `117026`.
- `rear_deck_C_21`: area `103370`.

`panels_fine` group totals:

- `nose_*`: 34 zones, total area `1634411`.
- `mid_*`: 16 zones, total area `1111233`.
- `rear_*`: 57 zones, total area `1347851`.

Broad-safe `panels_fine` examples:

- `nose_floor_C_09`: area `533460`.
- `mid_deck_C_160`: area `499815`.
- `nose_side_C_03`: area `343459`.
- `rear_side_C_30`: area `202330`.
- `mid_side_C_27`: area `178458`.
- `mid_floor_C_35`: area `151665`.
- `rear_deck_C_140`: area `133444`.
- `nose_floor_C_33`: area `110740`.
- `rear_side_C_152`: area `100162`.

Probe-only examples:

- `panels_high`: `rear_deck_C_06` area `3`, `rear_deck_C_62` area `14`,
  `rear_deck_C_18` area `150`, `nose_floor_C_67` area `816`.
- `panels_fine`: `rear_side_C_25` area `3`, `rear_deck_C_142` area `14`,
  `mid_deck_C_10` area `39`, `rear_deck_C_46` area `49`.

## Mesh And GBuffer Geometry

GBuffer axis roles from `resources/authoritative/gbuffer/extents_2048.json`:

| Role | Axis | Mesh-space min | Mesh-space max | Span |
| --- | ---: | ---: | ---: | ---: |
| `LAT` | 0 / X | -0.918999016 | 0.917999387 | 1.836998463 |
| `HGT` | 1 / Y | 0.147187531 | 1.055527687 | 0.908340156 |
| `LEN` | 2 / Z | -1.769556165 | 2.135099888 | 3.904655933 |

Local mesh evidence:

- All 13 OBJs have vertices, UVs, normals, and UV-referenced faces.
- Aggregate OBJ bounds are approximately min `[-0.91899973, 0.1470358,
  -1.7699338]`, max `[0.9190002, 1.056, 2.1355]`.
- Body OBJs cover almost the full atlas UV range and mesh length.
- Mudguard OBJs are separately named and have positive front Z/LEN ranges
  around `1.548..2.045`.
- Hub OBJs are separately named and sit around rear Z/LEN `-1.486..-0.819`.
- Pilot head OBJs sit around X/LAT `-0.148..0.148`, Y/HGT `0.681..1.022`,
  Z/LEN `-0.440..-0.074`.
- Left/right is supported by local component sign: local `L` components use
  positive X/LAT; local `R` components use negative X/LAT.

Important status:

- This supports code-driven painting by 3D position projected into the 2D UV
  atlas.
- It does not prove TMUF runtime visibility, DDS orientation, seam quality, or
  exact in-game panel interpretation until smoke testing.

## Paintable Panel Catalog

`out/reports/stock_part_inventory.json` currently exposes 26 paintable panel
targets. Every entry has a `symmetry_policy`, `source_status`,
`safe_design_scale`, source files, source zones, and
`tmuf_runtime_status=not_proven_until_smoke`.

Named PSD-only entries are strongest atlas evidence because they use
`psd_parts` labels without GBuffer placement. Mixed/generated entries are useful
for deeper panel control, but generated names support only local token evidence
such as `nose`, `mid`, `rear`, `deck`, `side`, and `floor`; they remain
experimental for runtime interpretation.

| Target | Evidence source | Design role |
| --- | --- | --- |
| `main_body_top_quadrants` | `psd_parts` zones 1-4 | Large base color separation, hard-edge blocks, black/red/white wedges. |
| `nose_identity_panel` | `NosePart` | Front identity wedge, spear tip, and number-free badge field. |
| `center_spine` | GBuffer `LAT` symmetry and `LEN` | Long top stripe, Gulf/Martini-style center system, black/red minimalist blade. |
| `engine_rear_deck` | low LEN/Z + high HGT/Y, `rear_deck_*` probes | Louvers, rear glow blocks, technical vents, symmetrical panel highlights. |
| `sidepod_blades` | `SideUnderColor_L/R`, `mid_side_*`, LAT sign | Large side sweeps, sponsor-like blank blocks, lower contrast fields. |
| `tailwing_bands` | `Tailwing_L/R`, `TailWingUnderBorderColor` | Rear identity stripe, metallic pinline, color echo visible from rear. |
| `front_mudguard_caps` | mudguard PSD labels + front LEN/Z | Accent caps, guard pinlines, black body with red/cyan edge highlights. |
| `rear_mudguard_caps` | mudguard PSD labels + rear LEN/Z | Rear color echo, darker guard caps, subtle wheel-arch rhythm. |
| `side_wings` | `SIdeWings`, `SideWingsUNDER` | Small aero flicks; useful for cyan/magenta/gold edge hits. |
| `mirrors_and_holders` | `SideMirrors`, `MirrorHolders` | Small color verification and polished micro-detail. |
| `helmet_and_visor` | `Helmet_*`, `HelmetGlass_*` | Optional driver color harmony; should not control main livery. |
| `underbody_dark` | `MainBodyUNDER_*`, `UnderPlate_*`, low HGT/Y | Dark material and shadow continuity, not hero graphics. |
| `licence_plate_blocks` | `LicencePlate`, `LicencePlateBlock` | Abstract plaque blocks and no-text graphic anchors. |
| `side_vent_inside` | `BigSideVentOneInSideColor` | Small vent interior accent and dark technical inset. |
| `rear_wheel_diffuse_blocks` | `RearWheelsSideBlock`, `KNob.Gouing.inside.Rear.wheel` | Rear wheel-adjacent Diffuse-only probe blocks; not `Details.dds`. |
| `front_mudguard_edge_details` | front mudguard edge/under/inside PSD zones | Front guard pinstripe edge, underside fill, and inner accent detail. |
| `rear_mudguard_edge_details` | rear mudguard edge/tip/under/inside PSD zones | Rear guard pinstripe edge, tip highlight, and underside fill. |
| `nose_deck_generated_panels` | generated `nose_deck_*` high panels | Front deck blocks, wedge clipping, and nose-adjacent color surfaces. |
| `nose_floor_generated_panels` | generated `nose_floor_*` fine panels | Front floor returns and lower wedge continuation probes. |
| `nose_side_generated_panels` | generated `nose_side_*` high panels | Front side sweeps and lower-side color returns. |
| `mid_deck_generated_panels` | generated `mid_deck_*` high panels | Cockpit-adjacent deck panels and mid-body geometric blocks. |
| `mid_side_generated_panel` | generated `mid_side_C_02` | Large mid-side speed blade field. |
| `mid_floor_generated_panels` | generated `mid_floor_*` fine panels | Mid-floor support blocks and lower shadow fields. |
| `rear_side_generated_panels` | generated `rear_side_*` fine panels | Symmetric rear side sweeps and side-to-tail transitions. |
| `rear_floor_generated_panels` | generated `rear_floor_*` high panels | Rear floor shadows and low rear accent returns. |
| `rear_deck_fine_louver_rows` | generated `rear_deck_*` fine panels | Fine rear deck louver rows, paired glow blocks, and technical vent rhythm. |

Important boundary: `nose_spear`, `side_blade`, `secondary_blade`,
`rear_louvers`, `rear_center_glow`, `shoulder_line`, `tail_bar`, and
`mudguard_edge` are generator masks in `src/stock_diffuse/panel_masks.py`.
They are not catalog entries unless represented by a higher-level target above,
and every one remains `experimental_until_tmuf_smoke` because it uses GBuffer
`LEN/LAT/HGT` predicates.

## Lessons From Old TM_CARS Generators

Reference-only reusable ideas:

- Smooth base gradients made skins look polished.
- Fewer, thicker, deliberate streamlines read better than noisy fields.
- Pinline/hood-band/cockpit-collar ideas gave hierarchy.
- Rear focal rings and spine accents worked when they were deliberate
  landmarks.
- Gloss/finish control mattered visually, but Diffuse alpha behavior is not yet
  proven for the stock lane.

Rejected for the stock Diffuse generator:

- Hardcoded old UV coordinates.
- Full-atlas random scatter as primary design language.
- Worn scratches, bleach, patina, and dust as dominant overlays.
- CH_2026/full-car operations such as wheel-disc fills, tyre fills,
  `Details.dds`, `ProjShad.dds`, custom GBX, underglow, or no-mudguard output.

## Design Lanes

Each lane uses reference-only inspiration and local geometry/label evidence.
No lane copies logos or exact real-world trade dress.

### 1. Minimal Black Red Wedge

Reference grammar:

- Honda MP4/4 supports low F1 geometry and long clean visual flow.
- Use only generic red/white/black wedge composition, no Marlboro mark.

Panels:

- `main_body_top_quadrants`
- `nose_spear`
- `center_spine`
- `sidepod_blades`
- `tailwing_bands`

Quality rule:

- Large black/charcoal negative space.
- One dominant red wedge and one narrow white separator.
- No random marks.

### 2. Black Gold Precision

Reference grammar:

- Classic Team Lotus source supports black/gold livery history.
- Use black base with thin gold trim, no JPS branding.

Panels:

- `center_spine`
- `shoulder_line`
- `tailwing_bands`
- `front_mudguard_caps`
- `rear_mudguard_caps`
- `mirrors_and_holders`

Quality rule:

- Gold is trim, not a large fill.
- Metallic look comes from value contrast and AO/prelight, not material claims.

### 3. Gulf-Style Two-Tone Prototype

Reference grammar:

- Gulf source supports orange/blue as recognizable motorsport livery grammar.
- Use adapted colors only, no Gulf logo or exact sponsor lockup.

Panels:

- `center_spine`
- `main_body_top_quadrants`
- `sidepod_blades`
- `tailwing_bands`

Quality rule:

- One broad center stripe plus side echo.
- Color blocks must be larger than fine-panel noise.

### 4. Martini-Style Flow Stripes

Reference grammar:

- Martini source supports blue/light-blue/red parallel stripe identity.
- Use a generic parallel stripe system, no ball/bar mark or exact trade dress.

Panels:

- `center_spine`
- `nose_spear`
- `sidepod_blades`
- `tailwing_bands`

Quality rule:

- Stripes stay parallel and readable through GBuffer `LEN`.
- Fine panels only clip stripe ends; they do not create random stripe fragments.

### 5. Technical Panel Map

Reference grammar:

- Porsche Pink Pig source supports panel/contour annotation as famous livery
  concept.
- Use dark technical cut lines or red contour lines, no meat-cut theme unless
  intentionally redesigned as abstract technical labels without text.

Panels:

- `panels_high` broad deck/side/floor groups.
- `panels_fine` only for contour accents after probe.

Quality rule:

- Lines follow panel groups and stay legible at distance.
- No small text until TMUF texture readability is proven.

### 6. BMW Art-Car Abstract

Reference grammar:

- BMW Art Cars support artist-designed racing cars with varied techniques.
- Tate/MoMA support abstraction, geometric abstraction, and controlled shape
  vocabulary.

Panels:

- `main_body_top_quadrants`
- `sidepod_blades`
- `tailwing_bands`
- selected broad `panels_high` zones.

Quality rule:

- Abstract shapes are still aligned to car flow: long forms along `LEN`,
  mirrored or intentionally asymmetric side balance across `LAT`.
- No full-atlas unbounded paint scatter.

### 7. Op-Art Speed Field

Reference grammar:

- Tate Op art supports geometric optical-effect vocabulary.

Panels:

- `sidepod_blades`
- `tailwing_bands`
- selected broad `mid_side`, `rear_side`, and `nose_side` panels.

Quality rule:

- Use large bands and controlled repetition.
- Avoid high-frequency moire; if it aliases in preview or TMUF, reject.

### 8. Dark Neon Prototype

Reference grammar:

- Old TM_CARS Tron variants support deliberate neon landmarks as reference
  only.
- Current stock generator already implements spine, side blade, rear louvers,
  tail bar, and mudguard edge masks.

Panels:

- Existing masks in `src/stock_diffuse/premium.py`.
- Future: add `tailwing_bands`, `side_wings`, and `mirrors_and_holders`.

Quality rule:

- Neon accents must be sparse, broad, and symmetrical enough to read as premium.
- No noisy cyber scatter.

## Generator Strategy

The stock generator should move from one neon recipe to a lane-based suite:

```text
recipes/stock_premium_suite.py
src/stock_diffuse/design_lanes.py
src/stock_diffuse/panel_masks.py
```

First implementation targets after calibration:

1. Add `panel_masks.py` with masks for named PSD families plus GBuffer-derived
   `nose_spear`, `center_spine`, `engine_rear_deck`, `sidepod_blades`, and
   `tailwing_bands`.
2. Add lane metadata with `source_evidence`, `local_panels_used`,
   `evidence_status`, and `rejected_assumptions`.
3. Generate candidates from multiple families, not only black/magenta/cyan:
   `minimal_black_red_wedge`, `black_gold_precision`,
   `gulf_two_tone_proto`, `martini_flow_dark`, `technical_panel_map`,
   `bmw_artcar_geometric`, `opart_speed_field`, and
   `dark_neon_prototype`.
4. Each report must include the exact masks, source lanes, risk classes, and
   `gbuffer_mapping=experimental_until_tmuf_smoke` until the smoke gate passes.

## Validation Gates

Before calibration smoke:

- Generate `calibration_stock_diffuse.zip`.
- Run local validators and inventory:
  `python3 recipes/validate_stock_outputs.py`,
  `python3 recipes/validate_profile_gates.py`,
  `python3 recipes/explore_stock_parts.py`,
  `python3 recipes/lab_status.py --write`.
- Treat GBuffer-driven placement as experimental.

Calibration smoke proof:

- Load the calibration zip in TMUF/TMNF.
- Confirm every observation explicitly:
  `nose_is_red`, `tail_is_blue`, `left_side_is_green`,
  `right_side_is_yellow`, `roof_high_surfaces_are_white`,
  `lower_floor_surfaces_are_dark`, `mudguards_are_magenta`,
  `centerline_is_cyan`, `package_loads_without_custom_gbx`.
- Record real screenshots with `recipes/record_tmuf_smoke.py`, using the
  required `front`, `side`, `rear`, and `top` screenshot roles.
- Evaluate and apply with `recipes/tmuf_smoke_gate.py`.

After calibration smoke:

- Generate lane candidates.
- Reject candidates that rely on tiny fragments, noisy scatter, hardcoded old
  UV coordinates, or unverified full-car features.
- Use preview and TMUF screenshots as visual acceptance evidence.
