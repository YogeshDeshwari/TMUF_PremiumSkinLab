# Reference Skin Batch Analysis

Evidence source:

- Imported ZIPs under `resources/reference_only/downloads/`
- Generated reports under `out/reference_analysis/`
- Generated package gallery: `out/reference_analysis/reference_package_gallery.png`
- Generated livery atlas gallery: `out/reference_analysis/reference_livery_atlas_gallery.png`
- Generated per-package contact sheets: `out/reference_analysis/*_contact_sheet.png`

This is reference-only evidence. These packages do not prove TMUF smoke status,
stock UV mapping, GBuffer accuracy, or generated-skin correctness.

The package gallery is a visual scanning aid for package identity and can choose
`Icon.dds`. The livery atlas gallery is the correct overview for paint analysis
because it prefers actual livery slots: `Diffuse.dds`, `Details.dds`, and dirty
map variants. Per-package contact sheets are still the safest review surface
because they show all detected DDS slots.

## Batch Result

28 user-provided packages were analyzed.

| Route | Count | Meaning |
| --- | ---: | --- |
| `stock_diffuse_only_reference` | 1 | Contains stock-format `Diffuse.dds` and `Icon.dds` only. Still reference-only. |
| `custom_fullcar_ch2026_reference` | 22 | Contains full-car custom package files and both GBX meshes match the CH_2026 donor hash comparison. |
| `custom_fullcar_partial_ch2026_mesh_reference` | 1 | Contains full-car custom package files and one GBX mesh matches the CH_2026 donor comparison. |
| `custom_fullcar_other_mesh_reference` | 4 | Contains full-car custom package files, but the GBX meshes do not match the CH_2026 donor comparison. |

## Style Metrics

Each report now includes `style_metrics`:

- `primary_livery_slot`: the livery texture slot with the strongest paint-surface signal.
- `slots`: per-DDS metrics for alpha visibility, contrast, luminance, and palette ratios.
- `dominant_palette_tags`: color-family tags derived from sampled RGB data.
- `does_not_prove_tmuf_smoke=true`: these are local image metrics only.

The metric sampler preserves RGB separately from alpha. This matters because
several reference packages have visible RGB data in a texture whose alpha is
fully transparent. Alpha is recorded, but RGB is still counted as visual design
evidence for analysis.

Current aggregate evidence from `reference_package_index.json`:

| Metric | Value |
| --- | --- |
| Primary livery slot `Diffuse.dds` | 23 packages |
| Primary livery slot `Details.dds` | 3 packages |
| Primary livery slot `details.dds` | 2 packages |
| `black` palette tag | 28 packages |
| `white` palette tag | 25 packages |
| `gray` palette tag | 24 packages |
| `red` palette tag | 10 packages |
| `cyan` palette tag | 6 packages |
| `blue` palette tag | 6 packages |
| `yellow_gold` palette tag | 4 packages |
| `magenta` palette tag | 2 packages |

Reference-only packages with notable color evidence:

- Magenta: `Deep-Galaxy-SKIN_by_MINA_TM.zip`,
  `CH_Bloom_Wheel_LED_Underglow.zip`.
- Cyan: `Aqua-Public-SKIN_by_MINA_TM.zip`, `Azerbaijan_by_kekfeg.zip`,
  `Incoming-Winter-Public-SKIN_by_MINA_TM.zip`,
  `Summer-2024-SKIN_by_MINA_TM.zip`, `Winter-SKIN_by_MINA_TM.zip`,
  `CH_Blu.zip`.
- Red: `hunter_by_WiiTRO.zip`, `Fall-Public-SKIN-_by_MINA_TM.zip`,
  `Azerbaijan_by_kekfeg.zip`, `flintstone_by_WiiTRO.zip`,
  `Christmas-2023-SKIN_by_MINA_TM.zip`, `Red-Public-SKIN_by_MINA_TM.zip`,
  `KEKW-Public-SKIN_by_MINA_TM.zip`,
  `KILL-la-KILL-Public-SKIN_by_MINA_TM.zip`,
  `Fallen-leaves-SKIN_by_MINA_TM.zip`, `(TMN_UF)_by_SparkyTM.zip`.

Evidence-backed generator guidance:

- Black/gray/white should remain the structural base family because it appears
  across nearly every strong reference.
- Magenta is rare in this batch, so black/magenta/cyan skins should keep magenta
  as a deliberate high-value accent instead of flooding every panel.
- Cyan appears more often than magenta and works well as a secondary blade,
  spine, or cold-light contrast color.
- Red is common and can support separate minimal black/red recipe lanes, but it
  should not be mixed into the first black/magenta/cyan proof family unless a
  recipe explicitly targets a red lane.
- `CH_Bloom_Wheel_LED_Underglow.zip` is the closest batch reference to the
  black/magenta/cyan direction, but it is CH_2026 full-car reference-only and
  must not be treated as stock mapping truth.

Generated stock guidance:

- `out/reports/reference_style_guidance.json` is built from this batch index and
  cited by premium stock reports.
- It carries `evidence_status=reference_metrics_not_tmuf_proof`.
- It is allowed to guide recipe metadata and palette choices.
- It is not stock UV evidence, not GBuffer proof, not TMUF runtime proof, and not
  part of stock `input_evidence`.

## Package Classification

| Package | Route | DDS | GBX | Donor Mesh Evidence | Notes |
| --- | --- | ---: | ---: | --- | --- |
| `minecart_by_WiiTRO.zip` | `custom_fullcar_other_mesh_reference` | 4 | 2 | neither GBX matches CH_2026 donor | visual/custom-mesh reference only |
| `hunter_by_WiiTRO.zip` | `custom_fullcar_partial_ch2026_mesh_reference` | 7 | 2 | `MainBody.Solid.Gbx` matches; high mesh differs | partial custom-mesh reference only |
| `Aqua-Public-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 4 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Fall-Public-SKIN-_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 4 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Azerbaijan_by_kekfeg.zip` | `stock_diffuse_only_reference` | 2 | 0 | no GBX files | only stock-format reference package in this batch |
| `flintstone_by_WiiTRO.zip` | `custom_fullcar_other_mesh_reference` | 7 | 2 | neither GBX matches CH_2026 donor | lowercase `diffuse.dds` and `details.dds` recorded |
| `steve-in-a-cart_by_WiiTRO.zip` | `custom_fullcar_other_mesh_reference` | 7 | 2 | neither GBX matches CH_2026 donor | `Projshad.dds` case variant recorded |
| `pedo-van_by_WiiTRO.zip` | `custom_fullcar_other_mesh_reference` | 7 | 2 | neither GBX matches CH_2026 donor | multiple lowercase texture names recorded |
| `Christmas-2023-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Incoming-Winter-Public-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 4 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Red-Public-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 4 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `KEKW-Public-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 3 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `KILL-la-KILL-Public-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 4 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Fallen-leaves-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Deep-Galaxy-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `(TMN_UF)_by_SparkyTM.zip` | `custom_fullcar_ch2026_reference` | 4 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Summer-2024-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Rameses-b-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Spring-2024-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Pink-Skin-(TMNF_UF)_by_SparkyTM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `MINA-2023-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `Winter-SKIN_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `KACKIEST-KACKY-9-SKIN-(white)_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `KACKIEST-KACKY-9-(black)_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `KACKIEST-KACKY-10-SKIN-(light-gray)_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `KACKIEST-KACKY-10-SKIN-(dark-gray)_by_MINA_TM.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `CH_Blu.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |
| `CH_Bloom_Wheel_LED_Underglow.zip` | `custom_fullcar_ch2026_reference` | 6 | 2 | both GBX files match CH_2026 donor | CH_2026 reference lane only |

## What We Can Use

Evidence-backed allowed use:

- Use color hierarchy and motif composition as visual reference.
- Use the CH_2026 matching packages only in the later CH_2026 full-car lane.
- Use packages with `ProjShad.dds`, `Details.dds`, dirty maps, and `Illum.dds`
  as examples of texture-slot packaging, not as proof that our stock generator
  should output those files.
- Use `Azerbaijan_by_kekfeg.zip` as a stock-format package reference because it
  contains only `Diffuse.dds` and `Icon.dds`, but still not as UV/GBuffer proof.

Evidence-backed blocked use:

- Do not use any custom full-car package as stock StadiumCar UV truth.
- Do not use CH_2026 donor-matching packages to decide stock mudguard, wheel,
  or Details.dds coordinates.
- Do not promote any reference package to `proven`; none of these reports include
  a TMUF runtime smoke test.
- Do not treat lowercase filename packages as canonical stock packaging.

## Visual Composition Lessons

These are visual observations from the generated atlas previews/contact sheets,
not TMUF runtime claims.

- The strongest MINA/Sparky-style examples use a dark neutral base with high
  contrast accents locked to repeated panels instead of random scatter.
- Readable skins usually reserve the brightest color for center spine, wing,
  side blade, or repeated nose/rear accents.
- Several seasonal/theme skins use the same structural pattern with different
  palette and surface fills, which supports a generator design where geometry
  masks drive composition and palettes are separate recipes.
- The CH_Blu and CH_Bloom packages demonstrate full texture-slot coordination:
  Diffuse, Details, dirty maps, and ProjShad work together. That is useful for
  the CH_2026 lane, but it is explicitly outside the first stock Diffuse-only
  milestone.
- The WiiTRO cart/sprite packages are useful evidence that external skins can
  include non-CH custom meshes and filename case variants. They are packaging
  references, not stock premium composition targets.
