from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.skin_dirs import DEFAULT_REPORT, build_skin_dir_report, write_skin_dir_report  # noqa: E402


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Find existing TMUF/TMNF StadiumCar skin directories.")
    parser.add_argument("--root", action="append", type=Path, help="search root; may be passed more than once")
    parser.add_argument(
        "--include-creation-targets",
        action="store_true",
        help="include recognized StadiumCar target paths that would need manual creation",
    )
    parser.add_argument("--max-depth", type=int, help="maximum directory depth below each root to scan")
    parser.add_argument("--write", type=Path, nargs="?", const=DEFAULT_REPORT, help="write JSON report")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)
    if args.max_depth is not None and args.max_depth < 0:
        parser.error("--max-depth must be zero or greater")

    roots = args.root if args.root else None
    report = build_skin_dir_report(
        roots,
        include_creation_targets=args.include_creation_targets,
        max_depth=args.max_depth,
    )
    if args.write is not None:
        write_skin_dir_report(
            args.write,
            roots,
            include_creation_targets=args.include_creation_targets,
            max_depth=args.max_depth,
        )

    if args.json:
        output = json.dumps(report, indent=2, sort_keys=True)
    else:
        lines = [
            f"status={report['status']}",
            f"candidate_count={report['candidate_count']}",
            f"max_depth={report['scan_boundary']['max_depth']}",
        ]
        lines.extend(f"candidate={candidate['path']}" for candidate in report["candidates"])
        lines.extend(f"manual_creation_target={target['path']}" for target in report["manual_creation_targets"])
        output = "\n".join(lines)

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "candidate_count" in main() else 1)
