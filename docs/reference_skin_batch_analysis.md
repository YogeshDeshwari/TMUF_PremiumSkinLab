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
