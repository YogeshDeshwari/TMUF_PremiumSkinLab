# Resource Usage

## Authoritative

These are copied into `resources/authoritative/`.

- Stock StadiumCar PSD
- Stock wireframe
- Local prelight/AO image
- Official visual mesh OBJ exports
- Label maps

The GBuffer arrays are stored beside authoritative inputs because they are
derived from the official visual mesh exports, but their evidence label is
`experimental` until calibration passes in TMUF.

## Reference Only

These are copied into `resources/reference_only/downloads/`.

- ManiaPark StadiumCar V2 primary skin
- ManiaPark StadiumCar V2 diffuse template
- TMNF-X community PSD
- StadiumCar HQ Templates pack
- UggHost guide and tutorial sample
- Modern Trackmania media pack
- `CH_Blu.zip`
- `CH_Bloom_Wheel_LED_Underglow.zip`
- User-provided reference skin batch from `Downloads`

Use these for comparison, not stock truth.

The two `CH_*` packages are CH_2026 custom full-car references. They include
`Details.dds`, `ProjShad.dds`, dirty maps, and GBX files, so they must not be
used as evidence for stock Diffuse-only StadiumCar mapping.

The imported reference skin batch is analyzed under `out/reference_analysis/`.
Current evidence from `reference_package_index.json`:

- 28 user-provided reference packages analyzed.
- 1 package is stock Diffuse/Icon format: `Azerbaijan_by_kekfeg.zip`.
- 22 packages exactly match the CH_2026 donor mesh pair.
- 1 package has partial CH_2026 donor mesh overlap: `hunter_by_WiiTRO.zip`.
- 4 packages use other custom meshes: `minecart_by_WiiTRO.zip`,
  `flintstone_by_WiiTRO.zip`, `steve-in-a-cart_by_WiiTRO.zip`, and
  `pedo-van_by_WiiTRO.zip`.
- Filename case variants are recorded in reports for `flintstone_by_WiiTRO.zip`,
  `steve-in-a-cart_by_WiiTRO.zip`, and `pedo-van_by_WiiTRO.zip`.

The package gallery at `out/reference_analysis/reference_package_gallery.png` is
a package-identity scanning aid and may choose `Icon.dds` when that is the most
readable slot. Use
`out/reference_analysis/reference_livery_atlas_gallery.png` for paint-slot
comparison because it prefers `Diffuse.dds`, `Details.dds`, and dirty-map
variants. Per-package contact sheets are the safest review surface because they
show all detected DDS slots.

## Experimental

These are copied into `resources/experimental/`.

- CH_2026 donor/custom mesh zip
- `canvas_compose`
- `remove_guards`

These are for later full-car profiles. They must not affect the stock Diffuse
lane.
