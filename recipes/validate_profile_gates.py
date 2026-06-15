from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.profiles.gates import evaluate_profile_gates  # noqa: E402


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Validate CH_2026 profile proof gates.")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    result = evaluate_profile_gates()
    if args.json:
        output = json.dumps(result, indent=2, sort_keys=True)
    else:
        fullcar = result["profiles"]["ch2026_fullcar"]["status"]
        nomud = result["profiles"]["ch2026_nomud"]["status"]
        output = "\n".join(
            [
                f"overall_status={result['overall_status']}",
                f"stock_calibration_gate={result['stock_calibration_gate']}",
                f"ch2026_fullcar={fullcar}",
                f"ch2026_nomud={nomud}",
            ]
        )
    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "custom_profiles" in main() else 1)
