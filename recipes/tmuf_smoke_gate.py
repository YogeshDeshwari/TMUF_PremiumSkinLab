from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.smoke_gate import apply_smoke_result, evaluate_smoke_report, plan_smoke_result, write_template  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or apply the TMUF calibration smoke-test gate.")
    parser.add_argument("--write-template", action="store_true", help="write out/proof/calibration_tmuf_smoke_template.json")
    parser.add_argument("--evaluate", type=Path, help="evaluate a filled TMUF smoke report without changing reports")
    parser.add_argument("--apply", type=Path, help="apply a passing TMUF smoke report to generated skin reports")
    parser.add_argument("--dry-run", action="store_true", help="with --apply, print the promotion plan without writing")
    parser.add_argument("--base-dir", type=Path, help="base directory for relative screenshot evidence paths")
    parser.add_argument("--report", action="append", type=Path, help="limit --apply/--dry-run to specific report path; may repeat")
    args = parser.parse_args()

    actions = [args.write_template, args.evaluate is not None, args.apply is not None]
    if sum(actions) != 1:
        parser.error("choose exactly one of --write-template, --evaluate, or --apply")
    if args.dry_run and args.apply is None:
        parser.error("--dry-run can only be used with --apply")
    if args.report and args.apply is None:
        parser.error("--report can only be used with --apply")

    if args.write_template:
        path = write_template()
        print(f"wrote {path}")
        return 0

    if args.evaluate is not None:
        print(json.dumps(evaluate_smoke_report(args.evaluate, base_dir=args.base_dir), indent=2, sort_keys=True))
        return 0

    if args.dry_run:
        print(
            json.dumps(
                plan_smoke_result(args.apply, report_paths=args.report, base_dir=args.base_dir),
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    updated = apply_smoke_result(args.apply, report_paths=args.report, base_dir=args.base_dir)
    for path in updated:
        print(f"updated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
