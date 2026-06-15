from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.smoke_record import DEFAULT_OUTPUT, record_calibration_smoke_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Record TMUF calibration smoke-test evidence.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="path to write calibration_tmuf_smoke.json")
    parser.add_argument("--base-dir", type=Path, default=ROOT, help="base directory used for relative screenshot paths")
    parser.add_argument("--tester", required=True, help="person or machine that performed the TMUF/TMNF smoke test")
    parser.add_argument("--tmuf-build", required=True, help="TMUF/TMNF build or install used for the smoke test")
    parser.add_argument("--test-date-local", required=True, help="local test date, for example 2026-06-15")
    parser.add_argument("--screenshot", action="append", type=Path, required=True, help="screenshot proving calibration observations")
    parser.add_argument("--notes", default="", help="optional smoke-test notes")
    parser.add_argument(
        "--all-required-observations-passed",
        action="store_true",
        help="explicitly confirm every required calibration observation passed in TMUF/TMNF",
    )
    args = parser.parse_args()

    path = record_calibration_smoke_report(
        output_path=args.output,
        tester=args.tester,
        tmuf_build=args.tmuf_build,
        test_date_local=args.test_date_local,
        screenshot_paths=args.screenshot,
        all_required_observations_passed=args.all_required_observations_passed,
        notes=args.notes,
        base_dir=args.base_dir,
    )
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
