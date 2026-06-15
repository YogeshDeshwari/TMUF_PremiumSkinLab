# TMUF Smoke Evidence Session

This folder is a capture scaffold only. It does not prove TMUF/TMNF
loaded the calibration skin and it does not prove GBuffer mapping.

Save real TMUF/TMNF screenshots at these exact paths:
- front: `/Users/ydeshwari/Documents/TMUF_PremiumSkinLab/out/proof/tmuf_smoke_session/screenshots/tmuf_calibration_front.png`
- side: `/Users/ydeshwari/Documents/TMUF_PremiumSkinLab/out/proof/tmuf_smoke_session/screenshots/tmuf_calibration_side.png`
- rear: `/Users/ydeshwari/Documents/TMUF_PremiumSkinLab/out/proof/tmuf_smoke_session/screenshots/tmuf_calibration_rear.png`
- top: `/Users/ydeshwari/Documents/TMUF_PremiumSkinLab/out/proof/tmuf_smoke_session/screenshots/tmuf_calibration_top.png`

Before recording evidence, verify every observation in TMUF/TMNF:
- nose_is_red
- tail_is_blue
- left_side_is_green
- right_side_is_yellow
- roof_high_surfaces_are_white
- lower_floor_surfaces_are_dark
- mudguards_are_magenta
- centerline_is_cyan
- package_loads_without_custom_gbx

After the screenshots exist, run:

```bash
python3 recipes/record_tmuf_smoke.py --tester 'manual tester' --tmuf-build 'TMUF local install' --test-date-local YYYY-MM-DD --install-receipt /Users/ydeshwari/Documents/TMUF_PremiumSkinLab/out/proof/tmuf_calibration_smoke_kit/proof/calibration_install_receipt.json --screenshot-role front=/Users/ydeshwari/Documents/TMUF_PremiumSkinLab/out/proof/tmuf_smoke_session/screenshots/tmuf_calibration_front.png --screenshot-role side=/Users/ydeshwari/Documents/TMUF_PremiumSkinLab/out/proof/tmuf_smoke_session/screenshots/tmuf_calibration_side.png --screenshot-role rear=/Users/ydeshwari/Documents/TMUF_PremiumSkinLab/out/proof/tmuf_smoke_session/screenshots/tmuf_calibration_rear.png --screenshot-role top=/Users/ydeshwari/Documents/TMUF_PremiumSkinLab/out/proof/tmuf_smoke_session/screenshots/tmuf_calibration_top.png --all-required-observations-passed --output /Users/ydeshwari/Documents/TMUF_PremiumSkinLab/out/proof/calibration_tmuf_smoke.json
```

The command will fail if any screenshot is missing, unreadable, or blank.
