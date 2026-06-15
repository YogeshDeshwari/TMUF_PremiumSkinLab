from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.evidence.reference_package_analysis import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    analyze_reference_package,
    write_reference_livery_atlas_gallery,
    write_reference_package_gallery,
    write_reference_package_index,
)


def main(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(description="Analyze external TMUF/TMNF skin reference packages.")
    parser.add_argument("packages", nargs="+", type=Path, help="reference zip package path")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="analysis output directory")
    parser.add_argument("--donor-zip", type=Path, help="optional donor zip for MainBody GBX hash comparison")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    reports = [
        analyze_reference_package(package, output_dir=args.output_dir, donor_zip=args.donor_zip)
        for package in args.packages
    ]
    gallery = write_reference_package_gallery(reports, args.output_dir)
    livery_gallery = write_reference_livery_atlas_gallery(reports, args.output_dir)
    index = write_reference_package_index(
        reports,
        args.output_dir,
        gallery=gallery,
        livery_gallery=livery_gallery,
    )
    summary = {
        "index": str(index),
        "gallery": str(gallery),
        "livery_atlas_gallery": str(livery_gallery),
        "reports": [report["output_artifacts"]["report"] for report in reports],
        "contact_sheets": [report["output_artifacts"]["contact_sheet"] for report in reports],
    }
    if args.json:
        output = json.dumps(summary, indent=2, sort_keys=True)
    else:
        lines = [f"index={index}"]
        lines.append(f"gallery={gallery}")
        lines.append(f"livery_atlas_gallery={livery_gallery}")
        lines.extend(f"report={path}" for path in summary["reports"])
        lines.extend(f"contact_sheet={path}" for path in summary["contact_sheets"])
        output = "\n".join(lines)

    if argv is None:
        print(output)
    return output


if __name__ == "__main__":
    main()
