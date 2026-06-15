from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.premium_review import (  # noqa: E402
    DEFAULT_RECEIPT,
    install_discovered_premium_review_skins,
    install_premium_review_skins,
    write_premium_review_receipt,
)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(
        description="Install current stock-safe premium candidate ZIPs for visual review only."
    )
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
    parser.add_argument("--receipt", type=Path, default=DEFAULT_RECEIPT, help="receipt JSON path")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    if args.install_skins_dir is not None and args.install_discovered:
        parser.error("--install-skins-dir and --install-discovered are mutually exclusive")
    if args.install_skins_dir is None and not args.install_discovered:
        parser.error("pass --install-skins-dir or --install-discovered")
    if args.search_root and not args.install_discovered:
        parser.error("--search-root requires --install-discovered")

    if args.install_discovered:
        result = install_discovered_premium_review_skins(args.search_root)
    else:
        result = install_premium_review_skins(args.install_skins_dir)
    receipt = write_premium_review_receipt(result, args.receipt)

    output_data = {
        **result,
        "receipt": str(receipt),
    }
    if args.json:
        output = json.dumps(output_data, indent=2, sort_keys=True)
    else:
        output = "\n".join(
            [
                f"status={result['status']}",
                f"install_target={result['install_target']}",
                f"candidate_count={result['candidate_count']}",
                f"receipt={receipt}",
                "does_not_prove_tmuf_smoke=true",
            ]
        )

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "installed_for_visual_review_not_tested" in main() else 1)
