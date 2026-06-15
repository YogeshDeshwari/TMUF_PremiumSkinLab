from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.lab_status import DEFAULT_STATUS_PATH, build_lab_status, write_lab_status  # noqa: E402


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Summarize current TMUF PremiumSkinLab proof status.")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--write", type=Path, nargs="?", const=DEFAULT_STATUS_PATH, help="write status JSON")
    args = parser.parse_args(argv)

    status = build_lab_status()
    if args.write is not None:
        write_lab_status(args.write)

    if args.json:
        output = json.dumps(status, indent=2, sort_keys=True)
    else:
        output = "\n".join(
            [
                f"objective_status={status['objective_status']}",
                f"stock_local_checks={status['stock']['local_checks_passed']}",
                f"stock_tmuf_smoke={status['stock']['tmuf_smoke_status']}",
                f"profile_status={status['profiles']['overall_status']}",
                f"smoke_kit={status['smoke_kit']['status']}",
                f"smoke_kit_fresh={status['smoke_kit']['fresh']}",
                f"skin_dir_candidates={status['skin_dirs']['candidate_count']}",
                f"smoke_readiness={status['smoke_readiness']['status']}",
                "next_required_evidence="
                + (",".join(status["next_required_evidence"]) if status["next_required_evidence"] else "none"),
            ]
        )

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "objective_status" in main() else 1)
