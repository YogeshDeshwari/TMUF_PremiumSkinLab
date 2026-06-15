from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.smoke_readiness import (  # noqa: E402
    DEFAULT_COMMAND_PACKET,
    DEFAULT_READINESS_PATH,
    build_smoke_readiness,
    write_smoke_command_packet,
    write_smoke_readiness,
)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Summarize readiness for manual TMUF calibration smoke testing.")
    parser.add_argument("--root", type=Path, default=ROOT, help="lab root to inspect")
    parser.add_argument("--install-target", type=Path, help="optional explicit StadiumCar folder to preflight without copying files")
    parser.add_argument("--write", type=Path, nargs="?", const=DEFAULT_READINESS_PATH, help="write readiness JSON")
    parser.add_argument(
        "--write-command-packet",
        type=Path,
        nargs="?",
        const=DEFAULT_COMMAND_PACKET,
        help="write a human-readable manual smoke command packet",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    readiness = build_smoke_readiness(args.root, install_target=args.install_target)
    if args.write is not None:
        write_smoke_readiness(args.write, args.root, install_target=args.install_target)
    command_packet = None
    if args.write_command_packet is not None:
        command_packet = write_smoke_command_packet(
            args.write_command_packet,
            args.root,
            install_target=args.install_target,
        )

    if args.json:
        json_data = dict(readiness)
        if command_packet is not None:
            json_data["command_packet"] = str(command_packet)
        output = json.dumps(json_data, indent=2, sort_keys=True)
    else:
        lines = [
            f"status={readiness['status']}",
            f"smoke_kit_fresh={readiness['smoke_kit']['fresh']}",
            f"skin_dir_candidates={readiness['skin_dirs']['candidate_count']}",
            f"install_receipt_valid={readiness['install_receipt']['valid']}",
            "next_actions=" + ",".join(readiness["next_actions"]),
        ]
        if command_packet is not None:
            lines.append(f"command_packet={command_packet}")
        output = "\n".join(lines)

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    raise SystemExit(0 if "status" in main() else 1)
