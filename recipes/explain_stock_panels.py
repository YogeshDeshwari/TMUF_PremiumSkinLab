from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.panel_deep_dive import (  # noqa: E402
    DEFAULT_JSON_OUTPUT,
    DEFAULT_MARKDOWN_OUTPUT,
    write_panel_deep_dive,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the evidence-backed stock panel deep dive")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN_OUTPUT)
    args = parser.parse_args()

    paths = write_panel_deep_dive(
        json_output=args.json_output,
        markdown_output=args.markdown_output,
    )
    print(f"wrote {paths['json_output']}")
    print(f"wrote {paths['markdown_output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
