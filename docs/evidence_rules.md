# Evidence Rules

## Labels

`proven`

Use for inputs whose role is backed by local source identity or local research
evidence. Example: the stock StadiumCar PSD copied from the local CarPark
reference.

`reference_only`

Use for material that can guide visual or technical decisions but must not
define stock TMUF truth. Example: ManiaPark StadiumCar V2 files, because V2 has
new mapping.

`experimental`

Use for material that may be useful only after a proof gate. Example: the
GBuffer arrays before TMUF calibration, and the CH_2026 full-car donor zip.

`rejected`

Use for material that should not be used as a source of truth for this target.
Example: modern Trackmania shader names as TMUF material logic.

## Current Evidence Decisions

Stock Diffuse route:

- Status: `proven`
- Reason: local research and stock-country-skin evidence support
  `Diffuse.dds` + `Icon.dds` as a valid stock skin package.

GBuffer route:

- Status: `experimental`
- Reason: local provenance is strong, but calibration must pass in TMUF before
  it becomes production truth.

StadiumCar V2:

- Status: `reference_only`
- Reason: it is useful TMUF-era package and visual reference, but its readme
  says it has new mapping.

CH_2026 full-car donor:

- Status: `experimental`
- Reason: it includes custom/donor GBX and full texture slots. It is not the
  official stock country-skin packaging.

Modern Trackmania media:

- Status: `reference_only` for general study, `rejected` as TMUF material truth.
- Reason: modern Trackmania uses a different shader/texture model.

