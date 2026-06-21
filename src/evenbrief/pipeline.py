"""Pipeline orchestrator for Even Brief edition generation.

Modes:
* ``--dry-run`` builds a fully schema-valid ``Edition`` from offline fixtures with
  NO API calls and NO ``ANTHROPIC_API_KEY`` - this is the CI/test path.
* normal mode runs discover -> research -> write -> verify (with markets + weather
  built alongside) -> assemble, writes the edition JSON and prints the cost meter.

Usage:
    python -m evenbrief.pipeline --dry-run --out content/editions/dryrun.json
    python -m evenbrief.pipeline --out content/editions/2026-06-22.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .schema import Edition

# Root of the repo (…/even-brief-site). This file is src/evenbrief/pipeline.py.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ARCHIVE_PATH = _REPO_ROOT / "archive.json"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _load_archive() -> list[dict]:
    """Read the root archive.json if present; return [] otherwise."""
    if _ARCHIVE_PATH.exists():
        try:
            data = json.loads(_ARCHIVE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _write_edition(edition: Edition, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        edition.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )


def _validate_roundtrip(out_path: Path) -> Edition:
    """Re-load the written JSON through ``Edition`` to prove it validates."""
    return Edition.model_validate_json(out_path.read_text(encoding="utf-8"))


def _build_meta():
    """Construct ``Meta`` from the real current London date/time."""
    from .schema import Meta

    # London time: BST (UTC+1) late Mar-late Oct, else GMT. Approximate via the
    # fixed +1h summer offset for the June window; fall back to UTC label safely.
    now_utc = datetime.now(timezone.utc)
    # Determine a rough BST/GMT label without zoneinfo dependency surprises.
    try:
        from zoneinfo import ZoneInfo
        london = now_utc.astimezone(ZoneInfo("Europe/London"))
        tz_label = "BST" if london.dst() else "GMT"
    except Exception:  # pragma: no cover - zoneinfo always present on 3.11+
        london = now_utc
        tz_label = "UTC"
    date_iso = london.strftime("%Y-%m-%d")
    date_display = london.strftime("%A, %-d %B %Y")
    edition_label = london.strftime("%-d %B %Y")
    compile_time = london.strftime("%H:%M ") + tz_label
    return Meta(
        date_iso=date_iso,
        date_display=date_display,
        edition_label=edition_label,
        compile_time=compile_time,
    )


# --------------------------------------------------------------------------- #
# Dry-run path
# --------------------------------------------------------------------------- #
def run_dry_run(out_path: Path) -> int:
    from .fixtures import build_dry_run_edition

    edition = build_dry_run_edition()
    _write_edition(edition, out_path)
    reloaded = _validate_roundtrip(out_path)
    print(f"[dry-run] wrote {out_path} ({len(reloaded.stories)} stories, "
          f"{len(reloaded.archive)} archive items) - validates against Edition.")
    return 0


# --------------------------------------------------------------------------- #
# Live path
# --------------------------------------------------------------------------- #
def run_live(out_path: Path) -> int:
    from .client import BriefingClient, CostMeter
    from .discover import discover_stories
    from .research import research_story
    from .write import write_story
    from .verify import verify_story
    from .markets import build_markets
    from .weather import build_weather

    meter = CostMeter()
    client = BriefingClient(meter=meter)

    meta = _build_meta()
    archive = _load_archive()

    # 1. Discover the slate.
    stubs = discover_stories(client, archive, meta.date_iso)
    print(f"[live] discovered {len(stubs)} stories")

    # 2-4. Research -> write -> verify each story.
    stories = []
    for stub in stubs:
        dossier = research_story(client, stub)
        story = write_story(client, dossier)
        story = verify_story(client, story, dossier)
        stories.append(story)
        print(f"[live] built story: {story.id}")

    # 5-6. Markets + weather.
    markets = build_markets(client, meta.date_iso)
    weather = build_weather(client)

    # 7. Assemble + validate.
    from .assemble import assemble_edition

    edition = assemble_edition(
        meta=meta,
        weather=weather,
        stories=stories,
        markets=markets,
        existing_archive=archive,
    )
    _write_edition(edition, out_path)
    _validate_roundtrip(out_path)

    # Update the root archive.json with the merged list.
    _ARCHIVE_PATH.write_text(
        json.dumps([a.model_dump() for a in edition.archive], indent=2),
        encoding="utf-8",
    )

    print(f"[live] wrote {out_path}")
    print(meter.summary())
    return 0


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an Even Brief edition.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Build a schema-valid edition from offline fixtures "
                             "(no API calls, no key required).")
    parser.add_argument("--out", default=None,
                        help="Output path for the edition JSON.")
    args = parser.parse_args(argv)

    out = Path(args.out) if args.out else None
    if out is None:
        # Default under content/editions/<date>.json.
        date = "dryrun" if args.dry_run else datetime.now().strftime("%Y-%m-%d")
        out = _REPO_ROOT / "content" / "editions" / f"{date}.json"

    try:
        if args.dry_run:
            return run_dry_run(out)
        return run_live(out)
    except Exception as exc:  # surface failure with nonzero exit for CI
        print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
