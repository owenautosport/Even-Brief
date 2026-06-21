"""Shared pytest fixtures.

The offline ``--dry-run`` edition is the backbone of the suite: it is a fully
schema-valid ``Edition`` produced with no network and no API key, so every
render / validate / dedupe test runs in CI for free.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def edition_path(tmp_path_factory) -> Path:
    """Generate the offline dry-run edition once per session."""
    from evenbrief import pipeline

    out = tmp_path_factory.mktemp("editions") / "dryrun.json"
    rc = pipeline.main(["--dry-run", "--out", str(out)])
    assert rc == 0, "pipeline --dry-run failed"
    assert out.exists()
    return out


@pytest.fixture(scope="session")
def edition(edition_path):
    from evenbrief.schema import Edition

    return Edition.model_validate_json(edition_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def rendered_html(edition) -> str:
    from build.render import render_html

    return render_html(edition)
