from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.premium_visual_review import (  # noqa: E402
    DEFAULT_OUTPUT,
    REQUIRED_PREMIUM_REVIEW_ROLES,
    record_premium_visual_review,
)


def _parse_screenshot_roles(values: list[str] | None) -> dict[str, Path]:
    roles: dict[str, Path] = {}
    for value in values or []:
        if "=" not in value:
            raise argparse.ArgumentTypeError(
                "screenshot roles must use role=path, for example front=/tmp/front.png"
            )
        role, raw_path = value.split("=", 1)
        role = role.strip()
        if role not in REQUIRED_PREMIUM_REVIEW_ROLES:
            raise argparse.ArgumentTypeError(
                f"unknown screenshot role {role!r}; expected one of {REQUIRED_PREMIUM_REVIEW_ROLES}"
            )
        if not raw_path.strip():
            raise argparse.ArgumentTypeError(f"screenshot path is empty for role {role!r}")
        roles[role] = Path(raw_path)
    return roles


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Record TMUF/TMNF visual review evidence for one premium candidate.")
    parser.add_argument("--skin-name", required=True, help="premium candidate skin name without .zip")
    parser.add_argument("--verdict", required=True, choices=["accepted", "needs_iteration", "rejected"])
    parser.add_argument("--tester", required=True, help="person or machine that performed the visual review")
    parser.add_argument("--tmuf-build", required=True, help="TMUF/TMNF build or install used for the review")
    parser.add_argument("--test-date-local", required=True, help="local review date, for example 2026-06-15")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="path to write the visual review JSON")
    parser.add_argument("--base-dir", type=Path, default=ROOT, help="base directory used for relative screenshot paths")
    parser.add_argument(
        "--screenshot-role",
        action="append",
        metavar="ROLE=PATH",
        required=True,
        help="role-labeled screenshot; required roles are front, side, rear, and top",
    )
    parser.add_argument("--notes", default="", help="manual visual feedback notes")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    try:
        screenshot_roles = _parse_screenshot_roles(args.screenshot_role)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    path = record_premium_visual_review(
        skin_name=args.skin_name,
        verdict=args.verdict,
        tester=args.tester,
        tmuf_build=args.tmuf_build,
        test_date_local=args.test_date_local,
        screenshot_roles=screenshot_roles,
        notes=args.notes,
        output_path=args.output,
        base_dir=args.base_dir,
    )
    data = {
        "status": "visual_review_recorded",
        "skin_name": args.skin_name,
        "verdict": args.verdict,
        "path": str(path),
        "does_not_prove_tmuf_smoke": True,
        "does_not_prove_gbuffer_mapping": True,
    }
    if args.json:
        output = json.dumps(data, indent=2, sort_keys=True)
    else:
        output = "\n".join(
            [
                "status=visual_review_recorded",
                f"skin_name={args.skin_name}",
                f"verdict={args.verdict}",
                f"path={path}",
                "does_not_prove_tmuf_smoke=true",
                "does_not_prove_gbuffer_mapping=true",
            ]
        )
    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "visual_review_recorded" in main() else 1)
