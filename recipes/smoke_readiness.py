from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.smoke_readiness import (  # noqa: E402
    DEFAULT_READINESS_PATH,
    build_smoke_readiness,
    write_smoke_readiness,
)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Summarize readiness for manual TMUF calibration smoke testing.")
    parser.add_argument("--root", type=Path, default=ROOT, help="lab root to inspect")
    parser.add_argument("--write", type=Path, nargs="?", const=DEFAULT_READINESS_PATH, help="write readiness JSON")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    readiness = build_smoke_readiness(args.root)
    if args.write is not None:
        write_smoke_readiness(args.write, args.root)

    if args.json:
        output = json.dumps(readiness, indent=2, sort_keys=True)
    else:
        output = "\n".join(
            [
                f"status={readiness['status']}",
                f"smoke_kit_fresh={readiness['smoke_kit']['fresh']}",
                f"skin_dir_candidates={readiness['skin_dirs']['candidate_count']}",
                f"install_receipt_valid={readiness['install_receipt']['valid']}",
                "next_actions=" + ",".join(readiness["next_actions"]),
            ]
        )

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "status" in main() else 1)
