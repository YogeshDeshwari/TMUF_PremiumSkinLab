from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any

from src.evidence.premium_visual_review import REQUIRED_PREMIUM_REVIEW_ROLES
from src.stock_diffuse.premium import CANDIDATE_NAMES


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SESSION_DIR = ROOT / "out" / "proof" / "premium_visual_review_session"
DEFAULT_OUTPUT_DIR = ROOT / "out" / "proof" / "premium_visual_review" / "reviews"
DEFAULT_VERDICT = "needs_iteration"


def _quote_command(parts: list[str | Path]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def _relative(path: Path, base_dir: Path) -> str:
    resolved = path.resolve()
    base = base_dir.resolve()
    try:
        return resolved.relative_to(base).as_posix()
    except ValueError:
        return resolved.as_posix()


def _candidate_names(candidate_names: list[str] | tuple[str, ...] | None) -> list[str]:
    names = list(candidate_names) if candidate_names is not None else list(CANDIDATE_NAMES)
    unknown = sorted(set(names) - set(CANDIDATE_NAMES))
    if unknown:
        raise ValueError(f"Unknown premium candidate(s): {unknown}")
    if not names:
        raise ValueError("At least one premium candidate is required")
    return names


def _record_command(
    *,
    skin_name: str,
    output_path: Path,
    base_dir: Path,
    screenshot_paths: dict[str, Path],
    default_verdict: str,
) -> str:
    parts: list[str | Path] = [
        "python3",
        "recipes/record_premium_visual_review.py",
        "--skin-name",
        skin_name,
        "--verdict",
        default_verdict,
        "--tester",
        "manual tester",
        "--tmuf-build",
        "TMUF local install",
        "--test-date-local",
        "YYYY-MM-DD",
        "--output",
        output_path,
        "--base-dir",
        base_dir,
    ]
    for role in REQUIRED_PREMIUM_REVIEW_ROLES:
        parts.extend(["--screenshot-role", f"{role}={screenshot_paths[role]}"])
    parts.extend(["--notes", "manual visual feedback", "--json"])
    return _quote_command(parts)


def _readme_text(manifest: dict[str, Any]) -> str:
    lines = [
        "# Premium Visual Review Session",
        "",
        "This folder is a capture scaffold only. It does not prove TMUF/TMNF",
        "loaded any premium skin, and it does not prove GBuffer mapping.",
        "",
        "For each candidate, save real TMUF/TMNF screenshots into the listed",
        "front, side, rear, and top paths, then run that candidate's command.",
        "",
        "Candidate commands:",
    ]
    for candidate in manifest["candidates"]:
        lines.extend(
            [
                "",
                f"## {candidate['skin_name']}",
                "",
                "Screenshot paths:",
            ]
        )
        for slot in candidate["screenshot_slots"]:
            lines.append(f"- {slot['role']}: `{slot['path']}`")
        lines.extend(["", "```bash", candidate["record_command"], "```"])
    lines.extend(
        [
            "",
            "Allowed verdicts are accepted, needs_iteration, and rejected.",
            "The record commands reject missing, unreadable, or blank screenshots.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_premium_visual_review_session(
    session_dir: Path = DEFAULT_SESSION_DIR,
    *,
    base_dir: Path = ROOT,
    output_dir: Path | None = None,
    candidate_names: list[str] | tuple[str, ...] | None = None,
    default_verdict: str = DEFAULT_VERDICT,
) -> dict[str, Any]:
    base = Path(base_dir)
    session = Path(session_dir)
    output_root = Path(output_dir) if output_dir is not None else base / "out" / "proof" / "premium_visual_review" / "reviews"
    names = _candidate_names(candidate_names)

    screenshots_dir = session / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)

    candidates: list[dict[str, Any]] = []
    command_lines: list[str] = []
    for name in names:
        candidate_screenshot_dir = screenshots_dir / name
        candidate_screenshot_dir.mkdir(parents=True, exist_ok=True)
        screenshot_paths = {
            role: candidate_screenshot_dir / f"{role}.png"
            for role in REQUIRED_PREMIUM_REVIEW_ROLES
        }
        output_path = output_root / f"{name}.json"
        command = _record_command(
            skin_name=name,
            output_path=output_path,
            base_dir=base,
            screenshot_paths=screenshot_paths,
            default_verdict=default_verdict,
        )
        command_lines.append(f"# {name}\n{command}")
        candidates.append(
            {
                "skin_name": name,
                "default_verdict": default_verdict,
                "output_report": _relative(output_path, base),
                "screenshot_slots": [
                    {
                        "role": role,
                        "path": str(screenshot_paths[role]),
                        "exists": screenshot_paths[role].exists(),
                        "required": True,
                    }
                    for role in REQUIRED_PREMIUM_REVIEW_ROLES
                ],
                "record_command": command,
            }
        )

    manifest = {
        "schema": "tmuf_premium_skin_lab.premium_visual_review_session.v1",
        "status": "awaiting_tmuf_premium_screenshots",
        "does_not_prove_tmuf_smoke": True,
        "does_not_prove_gbuffer_mapping": True,
        "base_dir": str(base),
        "session_dir": str(session),
        "screenshots_dir": str(screenshots_dir),
        "output_dir": _relative(output_root, base),
        "candidate_count": len(candidates),
        "required_screenshot_roles": REQUIRED_PREMIUM_REVIEW_ROLES,
        "candidates": candidates,
        "command_file": str(session / "record_premium_visual_review_commands.txt"),
        "readme": str(session / "README_premium_visual_review_session.md"),
        "proof_boundary": (
            "This session scaffold only prepares screenshot paths and review commands; "
            "it is not TMUF smoke evidence and does not prove GBuffer mapping."
        ),
    }
    (session / "session_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    (session / "record_premium_visual_review_commands.txt").write_text("\n\n".join(command_lines) + "\n")
    (session / "README_premium_visual_review_session.md").write_text(_readme_text(manifest))
    return manifest
