"""Validate an edition JSON against the schema, with friendly errors.

Used while hand-authoring an edition (Claude Code generation mode) to check the
draft before the full build:

    python -m evenbrief.check_edition content/editions/2026-06-22.json

Exits 0 and prints VALID, or exits 1 and lists each schema error as
``location: message`` so the author knows exactly what to fix.
"""
from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

from evenbrief.schema import Edition


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python -m evenbrief.check_edition <edition.json>", file=sys.stderr)
        return 2
    path = Path(argv[0])
    if not path.exists():
        print(f"no such file: {path}", file=sys.stderr)
        return 2
    try:
        ed = Edition.model_validate_json(path.read_text(encoding="utf-8"))
    except ValidationError as exc:
        print(f"INVALID — {len(exc.errors())} schema error(s) in {path}:", file=sys.stderr)
        for err in exc.errors():
            loc = ".".join(str(p) for p in err["loc"])
            print(f"  ✗ {loc}: {err['msg']}", file=sys.stderr)
        return 1

    print(
        f"VALID — {path.name}: {len(ed.stories)} stories, "
        f"{len(ed.archive)} new archive item(s), "
        f"{len(ed.markets.movers.indices)} indices, {len(ed.weather.days)}-day forecast."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
