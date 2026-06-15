from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.skin_dirs import create_stadiumcar_skin_dir  # noqa: E402
from src.evidence.smoke_kit import (  # noqa: E402
    build_smoke_kit,
    install_calibration_skin,
    install_discovered_calibration_skin,
    write_install_receipt,
)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Prepare TMUF calibration smoke-test files.")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "out" / "proof" / "tmuf_calibration_smoke_kit")
    parser.add_argument("--install-skins-dir", type=Path, help="existing TMUF/TMNF StadiumCar skin folder")
    parser.add_argument(
        "--install-discovered",
        action="store_true",
        help="install into the only StadiumCar skin folder found by discovery",
    )
    parser.add_argument(
        "--search-root",
        action="append",
        type=Path,
        help="discovery root for --install-discovered; may be passed more than once",
    )
    parser.add_argument(
        "--install-panel-probe",
        action="store_true",
        help="with an install target, also copy calibration_panel_family_probe.zip",
    )
    parser.add_argument(
        "--create-install-target",
        action="store_true",
        help="with --install-skins-dir, create the recognized StadiumCar target before installing",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    if args.install_skins_dir is not None and args.install_discovered:
        parser.error("--install-skins-dir and --install-discovered are mutually exclusive")
    if args.search_root and not args.install_discovered:
        parser.error("--search-root requires --install-discovered")
    if args.install_panel_probe and args.install_skins_dir is None and not args.install_discovered:
        parser.error("--install-panel-probe requires --install-skins-dir or --install-discovered")
    if args.create_install_target and args.install_skins_dir is None:
        parser.error("--create-install-target requires --install-skins-dir")

    discovery_roots = args.search_root if args.search_root else None
    result = build_smoke_kit(args.out_dir, discovery_roots=discovery_roots)
    if args.install_skins_dir is not None:
        install_target_setup = None
        if args.create_install_target:
            install_target_setup = create_stadiumcar_skin_dir(args.install_skins_dir)
        result["install"] = install_calibration_skin(
            args.install_skins_dir,
            include_panel_probe=args.install_panel_probe,
        )
        if install_target_setup is not None:
            result["install"]["selection_mode"] = "explicit_install_target_created"
            result["install"]["install_target_setup"] = install_target_setup
        result["install_receipt"] = str(write_install_receipt(result["install"], args.out_dir))
    elif args.install_discovered:
        result["install"] = install_discovered_calibration_skin(
            discovery_roots,
            include_panel_probe=args.install_panel_probe,
        )
        result["install_receipt"] = str(write_install_receipt(result["install"], args.out_dir))

    if args.json:
        output = json.dumps(result, indent=2, sort_keys=True)
    else:
        lines = [
            f"status={result['status']}",
            f"kit_dir={result['kit_dir']}",
            f"zip={result['zip']}",
            f"calibration_skin={result['calibration_skin']}",
        ]
        if "install" in result:
            lines.append(f"installed_skin={result['install']['installed_skin']}")
            for supplemental in result["install"].get("installed_supplemental_skins", []):
                lines.append(f"installed_supplemental_skin={supplemental['installed_skin']}")
            lines.append(f"install_receipt={result['install_receipt']}")
            lines.append("install_status=installed_not_tested")
        output = "\n".join(lines)

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "not_run" in main() else 1)
