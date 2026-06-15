from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.smoke_session import (  # noqa: E402
    DEFAULT_INSTALL_RECEIPT,
    DEFAULT_SESSION_DIR,
    build_smoke_session,
)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Prepare exact screenshot paths for TMUF calibration smoke evidence.")
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION_DIR, help="directory for smoke session files")
    parser.add_argument("--install-receipt", type=Path, default=DEFAULT_INSTALL_RECEIPT, help="install receipt to cite")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    manifest = build_smoke_session(args.session_dir, install_receipt=args.install_receipt)
    if args.json:
        output = json.dumps(manifest, indent=2, sort_keys=True)
    else:
        lines = [
            f"status={manifest['status']}",
            f"session_dir={manifest['session_dir']}",
            f"screenshots_dir={manifest['screenshots_dir']}",
            f"install_receipt_valid={manifest['install_receipt_valid']}",
            f"record_command_file={manifest['record_command_file']}",
            "does_not_prove_tmuf_smoke=true",
        ]
        output = "\n".join(lines)

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "awaiting_tmuf_screenshots" in main() else 1)
