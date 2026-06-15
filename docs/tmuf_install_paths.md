# TMUF/TMNF StadiumCar Install Path Evidence

This document is evidence for smoke-test setup only. It does not prove that a
skin loaded in TMUF/TMNF, and it does not prove GBuffer mapping.

## Stock StadiumCar Skin Target

Preferred first target for a normal user-data install:

```text
~/Documents/TrackMania/Skins/Vehicles/StadiumCar
```

Evidence status: `reference_only_install_path_guidance`.

Why this is the first target:

- GameBanana's TMNF car install tutorial lists the path as
  `Documents\TrackMania\Skins\Vehicles\StadiumCar`.
- A TMNF-X help thread describes creating `Vehicles`, then `StadiumCar`, and
  copying the car skin into that folder.
- A TrackMania Reddit support thread reports the same practical behavior: the
  folder may not exist until a skin is saved or the user creates it manually.

Sources:

- https://gamebanana.com/tuts/11382
- https://tmnf.exchange/threadshow/6438?p=1
- https://www.reddit.com/r/TrackMania/comments/1892a9p/how_to_download_trackmania_nations_forever_on/

## Alternate Recognized Suffixes

The tooling still recognizes these suffixes because local packages and older
guides can distinguish user-data skins, install-data skins, and model packages:

```text
Skins/Vehicles/StadiumCar
Skins/Models/StadiumCar
GameData/Skins/Vehicles/StadiumCar
```

For the current stock Diffuse calibration route, `Skins/Vehicles/StadiumCar`
under the `TrackMania` documents folder is the recommended first setup target.
`Skins/Models/CarCommon` appears in some custom model guidance, but it is not
the first target for the stock `Diffuse.dds` + `Icon.dds` calibration ZIP.

## Proof Boundary

Creating the folder and copying `calibration_stock_diffuse.zip` only proves:

```text
folder prepared
zip copied
receipt written
```

It does not prove:

```text
TMUF/TMNF loaded the skin
the stock Diffuse route is visually correct
GBuffer placement aligns in-game
premium candidates are accepted visually
```

Those require the manual TMUF/TMNF smoke report and screenshots described in
`docs/tmuf_smoke_test.md`.
