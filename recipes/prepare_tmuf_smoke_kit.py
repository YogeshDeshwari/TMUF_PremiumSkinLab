from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.smoke_kit import (  # noqa: E402
    build_smoke_kit,
    install_calibration_skin,
    write_install_receipt,
)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Prepare TMUF calibration smoke-test files.")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "out" / "proof" / "tmuf_calibration_smoke_kit")
    parser.add_argument("--install-skins-dir", type=Path, help="existing TMUF/TMNF StadiumCar skin folder")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    result = build_smoke_kit(args.out_dir)
    if args.install_skins_dir is not None:
        result["install"] = install_calibration_skin(args.install_skins_dir)
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
            lines.append(f"install_receipt={result['install_receipt']}")
            lines.append("install_status=installed_not_tested")
        output = "\n".join(lines)

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "not_run" in main() else 1)
