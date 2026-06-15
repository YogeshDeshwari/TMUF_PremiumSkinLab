from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.post_smoke_selftest import run_synthetic_post_smoke_selftest  # noqa: E402


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(
        description="Run a synthetic post-smoke validation in a temporary copy. This does not prove TMUF smoke.",
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="scratch workspace to create; existing paths are removed only when previously marked synthetic",
    )
    parser.add_argument("--json", action="store_true", help="print the full JSON report")
    args = parser.parse_args(argv)

    result = run_synthetic_post_smoke_selftest(
        source_root=ROOT,
        workspace_root=args.workspace,
    )
    if args.json:
        output = json.dumps(result, indent=2, sort_keys=True)
    else:
        output = (
            "synthetic_smoke=True "
            f"stock_completion={result['stock']['completion_status']} "
            f"stock_tmuf_smoke={result['stock']['tmuf_smoke_status']} "
            f"ch2026_fullcar={result['profiles']['profiles']['ch2026_fullcar']['status']} "
            "claims_real_tmuf_proof=False"
        )
    print(output)
    return output


if __name__ == "__main__":
    main()
