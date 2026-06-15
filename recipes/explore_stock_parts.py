from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.part_inventory import build_part_inventory  # noqa: E402


DEFAULT_OUTPUT = ROOT / "out" / "reports" / "stock_part_inventory.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write an evidence-backed stock StadiumCar part inventory")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    inventory = build_part_inventory()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
