from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.smoke_record import DEFAULT_OUTPUT, record_calibration_smoke_report  # noqa: E402
from src.evidence.smoke_gate import REQUIRED_OBSERVATIONS, REQUIRED_SCREENSHOT_ROLES  # noqa: E402


def _parse_screenshot_roles(values: list[str] | None) -> dict[str, Path]:
    roles: dict[str, Path] = {}
    for value in values or []:
        if "=" not in value:
            raise argparse.ArgumentTypeError(
                "screenshot roles must use role=path, for example front=/tmp/front.png"
            )
        role, raw_path = value.split("=", 1)
        role = role.strip()
        if role not in REQUIRED_SCREENSHOT_ROLES:
            raise argparse.ArgumentTypeError(
                f"unknown screenshot role {role!r}; expected one of {REQUIRED_SCREENSHOT_ROLES}"
            )
        if not raw_path.strip():
            raise argparse.ArgumentTypeError(f"screenshot path is empty for role {role!r}")
        roles[role] = Path(raw_path)
    return roles


def main() -> int:
    parser = argparse.ArgumentParser(description="Record TMUF calibration smoke-test evidence.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="path to write calibration_tmuf_smoke.json")
    parser.add_argument("--base-dir", type=Path, default=ROOT, help="base directory used for relative screenshot paths")
    parser.add_argument("--tester", required=True, help="person or machine that performed the TMUF/TMNF smoke test")
    parser.add_argument("--tmuf-build", required=True, help="TMUF/TMNF build or install used for the smoke test")
    parser.add_argument("--test-date-local", required=True, help="local test date, for example 2026-06-15")
    parser.add_argument(
        "--install-receipt",
        type=Path,
        help="optional calibration_install_receipt.json from recipes/prepare_tmuf_smoke_kit.py --install-skins-dir",
    )
    parser.add_argument(
        "--screenshot-role",
        action="append",
        metavar="ROLE=PATH",
        required=True,
        help="role-labeled screenshot; required roles are front, side, rear, and top",
    )
    parser.add_argument(
        "--confirm-observation",
        action="append",
        choices=REQUIRED_OBSERVATIONS,
        help="confirm one required calibration observation; pass once for each required observation",
    )
    parser.add_argument("--notes", default="", help="optional smoke-test notes")
    parser.add_argument(
        "--all-required-observations-passed",
        action="store_true",
        help="explicitly confirm every required calibration observation passed in TMUF/TMNF",
    )
    args = parser.parse_args()
    try:
        screenshot_roles = _parse_screenshot_roles(args.screenshot_role)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    path = record_calibration_smoke_report(
        output_path=args.output,
        tester=args.tester,
        tmuf_build=args.tmuf_build,
        test_date_local=args.test_date_local,
        screenshot_roles=screenshot_roles,
        all_required_observations_passed=args.all_required_observations_passed,
        confirmed_observations=args.confirm_observation,
        install_receipt=args.install_receipt,
        notes=args.notes,
        base_dir=args.base_dir,
    )
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
