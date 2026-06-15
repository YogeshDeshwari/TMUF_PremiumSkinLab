from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.stock_validator import validate_stock_outputs  # noqa: E402


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Validate generated stock Diffuse skin artifacts.")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    result = validate_stock_outputs()
    if args.json:
        output = json.dumps(result, indent=2, sort_keys=True)
    else:
        output = "\n".join(
            [
                f"local_checks_passed={result['local_checks_passed']}",
                f"tmuf_smoke_status={result['tmuf_smoke_status']}",
                f"completion_status={result['completion_status']}",
                f"errors={len(result['errors'])}",
                f"warnings={','.join(result['warnings']) if result['warnings'] else 'none'}",
            ]
        )
    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    output = main()
    raise SystemExit(0 if "local_checks_passed=True" in output or '"local_checks_passed": true' in output else 1)
