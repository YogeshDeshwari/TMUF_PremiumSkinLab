from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.premium_visual_review_session import (  # noqa: E402
    DEFAULT_SESSION_DIR,
    build_premium_visual_review_session,
)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Prepare screenshot paths for premium candidate visual review.")
    parser.add_argument("--session-dir", type=Path, default=DEFAULT_SESSION_DIR, help="directory for review session files")
    parser.add_argument("--base-dir", type=Path, default=ROOT, help="base directory for output report paths")
    parser.add_argument(
        "--candidate",
        action="append",
        help="premium candidate to include; repeat for multiple candidates; omit for all candidates",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    manifest = build_premium_visual_review_session(
        args.session_dir,
        base_dir=args.base_dir,
        candidate_names=args.candidate,
    )
    if args.json:
        output = json.dumps(manifest, indent=2, sort_keys=True)
    else:
        output = "\n".join(
            [
                f"status={manifest['status']}",
                f"session_dir={manifest['session_dir']}",
                f"screenshots_dir={manifest['screenshots_dir']}",
                f"candidate_count={manifest['candidate_count']}",
                f"command_file={manifest['command_file']}",
                "does_not_prove_tmuf_smoke=true",
                "does_not_prove_gbuffer_mapping=true",
            ]
        )

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "awaiting_tmuf_premium_screenshots" in main() else 1)
