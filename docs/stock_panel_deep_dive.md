# Stock Panel Deep Dive

This is generated from the stock part inventory and candidate reports. It is evidence for local atlas targeting, not proof of TMUF runtime visibility.

## Evidence Boundary

- Stock route: `stock_diffuse_only`.
- TMUF runtime status: `not_proven_until_smoke`.
- Catalog targets: `26`.
- Source status counts: `experimental_until_tmuf_smoke=1, mixed_generated_labels_and_experimental_gbuffer=10, mixed_local_label_and_experimental_gbuffer=3, proven_local_label_map=12`.
- Runtime status counts: `not_proven_until_smoke=26`.
- Label maps: `psd_parts=41`, `panels_high=60`, `panels_fine=107`.

Known limits:
- no roof named PSD zone.
- no DDS orientation claim until TMUF smoke.
- no UV seam quality claim until TMUF smoke.
- no material gloss claim from Diffuse alpha until TMUF smoke.
- generated panel names provide token evidence only.

## Surface Families

### front_nose_centerline

Front identity, nose flow, splitter-like support panels, and centerline probes.

Source status counts: `experimental_until_tmuf_smoke=1, mixed_generated_labels_and_experimental_gbuffer=3, mixed_local_label_and_experimental_gbuffer=1, proven_local_label_map=3`. Runtime status counts: `not_proven_until_smoke=8`.

| Target | Source status | Runtime status | Area | Use |
| --- | --- | --- | ---: | --- |
| `nose_identity_panel` | `proven_local_label_map` | `not_proven_until_smoke` | 101934 | front identity wedge, spear tip, and number-free badge field |
| `center_spine` | `experimental_until_tmuf_smoke` | `not_proven_until_smoke` | 1622702 | long center stripe, symmetry probe, and top-flow alignment |
| `nose_deck_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 220398 | front deck blocks, wedge clipping, and large nose-adjacent color surfaces |
| `nose_floor_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 788929 | front floor returns, lower wedge continuation, and dark/bright underside split probes |
| `nose_side_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 1078213 | front side sweeps and large lower-side color returns |
| `side_wings` | `proven_local_label_map` | `not_proven_until_smoke` | 125401 | small aero flicks and secondary color hits |
| `front_mudguard_caps` | `mixed_local_label_and_experimental_gbuffer` | `not_proven_until_smoke` | 192838 | front guard caps, edge highlights, and calibration-visible color checks |
| `front_mudguard_edge_details` | `proven_local_label_map` | `not_proven_until_smoke` | 111436 | front guard pinstripe edge, underside fill, and inner accent details |

### cockpit_mid_deck

Top body quadrants, cockpit-adjacent deck fields, large flank panels, and pilot harmony.

Source status counts: `mixed_generated_labels_and_experimental_gbuffer=3, proven_local_label_map=3`. Runtime status counts: `not_proven_until_smoke=6`.

| Target | Source status | Runtime status | Area | Use |
| --- | --- | --- | ---: | --- |
| `main_body_top_quadrants` | `proven_local_label_map` | `not_proven_until_smoke` | 1622702 | large base fields, hard-edge blocks, long stripe clipping, and broad abstract panels |
| `mid_deck_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 723443 | cockpit-adjacent deck panels, roof flow breaks, and mid-body geometric blocks |
| `mid_side_generated_panel` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 623575 | large mid-side field for readable speed blades and blank sponsor-like geometry without text |
| `mid_floor_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 196123 | mid-floor support blocks, lower shadow fields, and underside accent probes |
| `helmet_and_visor` | `proven_local_label_map` | `not_proven_until_smoke` | 622098 | driver color harmony and restrained glass/visor shading |
| `side_vent_inside` | `proven_local_label_map` | `not_proven_until_smoke` | 19322 | small vent interior accent and dark technical inset |

### side_flanks_aero

Sidepod blades, side winglets, mirrors, vents, and side-to-tail color rhythm.

Source status counts: `mixed_generated_labels_and_experimental_gbuffer=2, mixed_local_label_and_experimental_gbuffer=1, proven_local_label_map=4`. Runtime status counts: `not_proven_until_smoke=7`.

| Target | Source status | Runtime status | Area | Use |
| --- | --- | --- | ---: | --- |
| `sidepod_blades` | `mixed_local_label_and_experimental_gbuffer` | `not_proven_until_smoke` | 263234 | lower side sweeps, sponsor-like blank blocks, and side color returns |
| `mid_side_generated_panel` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 623575 | large mid-side field for readable speed blades and blank sponsor-like geometry without text |
| `rear_side_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 383268 | rear side sweeps, color echoes, and side-to-tail transitions |
| `side_wings` | `proven_local_label_map` | `not_proven_until_smoke` | 125401 | small aero flicks and secondary color hits |
| `mirrors_and_holders` | `proven_local_label_map` | `not_proven_until_smoke` | 47755 | small contrast checks and polished micro-detail |
| `side_vent_inside` | `proven_local_label_map` | `not_proven_until_smoke` | 19322 | small vent interior accent and dark technical inset |
| `tailwing_bands` | `proven_local_label_map` | `not_proven_until_smoke` | 177929 | rear wing bands, edge trim, and high-contrast rear identity |

### rear_engine_tail

Rear deck, louver rows, tailwing bands, rear guard rhythm, and lower rear support panels.

Source status counts: `mixed_generated_labels_and_experimental_gbuffer=4, mixed_local_label_and_experimental_gbuffer=1, proven_local_label_map=2`. Runtime status counts: `not_proven_until_smoke=7`.

| Target | Source status | Runtime status | Area | Use |
| --- | --- | --- | ---: | --- |
| `engine_rear_deck` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 480151 | rear deck louvers, glow blocks, technical vent rhythm, and symmetric rear highlights |
| `rear_deck_fine_louver_rows` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 272437 | fine rear deck louver rows, paired glow blocks, and technical vent rhythm |
| `rear_side_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 383268 | rear side sweeps, color echoes, and side-to-tail transitions |
| `rear_floor_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | 256274 | rear floor shadows, dark support fields, and low rear accent returns |
| `tailwing_bands` | `proven_local_label_map` | `not_proven_until_smoke` | 177929 | rear wing bands, edge trim, and high-contrast rear identity |
| `rear_mudguard_caps` | `mixed_local_label_and_experimental_gbuffer` | `not_proven_until_smoke` | 232502 | rear guard caps, rear color echo, and wheel-arch rhythm |
| `rear_mudguard_edge_details` | `proven_local_label_map` | `not_proven_until_smoke` | 159801 | rear guard pinstripe edge, tip highlight, and underside fill |

### support_auxiliary

Non-hero support surfaces that can polish a skin without proving custom materials.

Source status counts: `proven_local_label_map=5`. Runtime status counts: `not_proven_until_smoke=5`.

| Target | Source status | Runtime status | Area | Use |
| --- | --- | --- | ---: | --- |
| `underbody_dark` | `proven_local_label_map` | `not_proven_until_smoke` | 489634 | dark material continuity, low reflections, and non-hero shadow fields |
| `licence_plate_blocks` | `proven_local_label_map` | `not_proven_until_smoke` | 143240 | abstract plaque blocks, small color balance fields, and no-text graphic anchors |
| `rear_wheel_diffuse_blocks` | `proven_local_label_map` | `not_proven_until_smoke` | 64829 | stock Diffuse rear wheel-adjacent blocks and tiny mechanical color echoes |
| `helmet_and_visor` | `proven_local_label_map` | `not_proven_until_smoke` | 622098 | driver color harmony and restrained glass/visor shading |
| `mirrors_and_holders` | `proven_local_label_map` | `not_proven_until_smoke` | 47755 | small contrast checks and polished micro-detail |

## More Panel Opportunities

| Target | Source status | Runtime status | Current candidates | Why it matters |
| --- | --- | --- | --- | --- |
| `mid_deck_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | black_cyan_spine, magenta_cyan_race_proto | large cockpit and roof-flow deck fields for symmetric extra panels near the engine cover. |
| `mid_side_generated_panel` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | magenta_cyan_race_proto, violet_cyber_flow | very large flank field for broad side blades and blank sponsor-like geometry without text. |
| `rear_deck_fine_louver_rows` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | dark_neon_louver | fine rear deck rows for technical louver rhythm and paired glow accents. |
| `nose_floor_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | black_magenta_cyan_blade | front floor returns for splitter-like lower wedge continuation probes. |
| `rear_floor_generated_panels` | `mixed_generated_labels_and_experimental_gbuffer` | `not_proven_until_smoke` | dark_neon_louver | low rear support blocks for shadow fields and tail color echoes. |

## Generator Masks, Not Catalog Panels

These masks are useful for painting composition, but they are not named stock panel catalog targets. They stay experimental until TMUF smoke evidence validates the GBuffer-driven placement.

| Mask | Evidence status | Pixel count | Use |
| --- | --- | ---: | --- |
| `body` | `experimental_until_tmuf_smoke` | 4103418 | Whole stock atlas footprint used by the current stock generator. |
| `upper` | `experimental_until_tmuf_smoke` | 2145447 | High body surfaces selected by HGT/Y after GBuffer projection. |
| `lower` | `experimental_until_tmuf_smoke` | 1957971 | Low body surfaces selected by HGT/Y after GBuffer projection. |
| `nose_spear` | `experimental_until_tmuf_smoke` | 205498 | Front spear selected by positive LEN and center symmetry. |
| `side_blade` | `experimental_until_tmuf_smoke` | 59701 | Lower side blade selected by side-band height and lateral symmetry. |
| `secondary_blade` | `experimental_until_tmuf_smoke` | 34918 | Secondary lower side blade offset from the primary blade. |
| `rear_louvers` | `experimental_until_tmuf_smoke` | 122550 | Rear deck louver rhythm selected by LEN/HGT/symmetry. |
| `rear_center_glow` | `experimental_until_tmuf_smoke` | 159717 | Centered rear deck focal accent. |
| `shoulder_line` | `experimental_until_tmuf_smoke` | 44664 | Upper shoulder pinline selected by HGT/LEN/symmetry. |
| `tail_bar` | `experimental_until_tmuf_smoke` | 194475 | Rear transverse accent selected by low LEN and HGT. |
| `mudguard_edge` | `experimental_until_tmuf_smoke` | 414363 | Mudguard edge accent combining PSD mudguards and GBuffer position. |

## Aliases

- `front_splitter_floor_probe` -> `nose_floor_generated_panels`
- `front_winglet_panels` -> `side_wings`
- `upper_center_roof_spine` -> `center_spine + main_body_top_quadrants`
- `nose_top_deck_panels` -> `nose_deck_generated_panels`
- `engine_louver_rows` -> `rear_deck_fine_louver_rows`
- `large_side_flank_panel` -> `mid_side_generated_panel`

## Locked Or Non-Stock Routes

| Route | Status | Why locked |
| --- | --- | --- |
| `Details.dds` | `locked_custom_profile` | not stock_diffuse_only; belongs behind the CH_2026 full-car proof gate; does not prove tyre sidewall, tread, hub material, or stock wheel routing |
| `ProjShad.dds` | `locked_custom_profile` | not stock_diffuse_only; optional underglow/shadow route only after CH_2026 full-car proof |
| `custom mesh / no mudguard` | `locked_custom_profile` | not stock_diffuse_only; custom GBX and no-mudguard work cannot be used in the stock generator |
