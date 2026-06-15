from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.skin_dirs import create_stadiumcar_skin_dir  # noqa: E402


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Create an explicit recognized TMUF/TMNF StadiumCar skin folder.")
    parser.add_argument("--target", type=Path, required=True, help="target path ending in a recognized StadiumCar suffix")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    result = create_stadiumcar_skin_dir(args.target)
    if args.json:
        output = json.dumps(result, indent=2, sort_keys=True)
    else:
        output = "\n".join(
            [
                f"status={result['status']}",
                f"path={result['path']}",
                f"route={result['route']}",
                f"created={str(result['created']).lower()}",
                "does_not_prove_tmuf_smoke=true",
            ]
        )

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "directory_ready_not_tested" in main() else 1)
