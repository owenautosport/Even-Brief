"""Archive merge (Claude Code mode only needs today's items) + check CLI."""
from __future__ import annotations

from pathlib import Path

from build.render import effective_archive
from evenbrief import check_edition

ROOT = Path(__file__).resolve().parent.parent


def test_merge_folds_in_prior_and_strips_stale_panels(edition):
    prior = [
        # an older edition's story still carrying a (now-dead) panel link
        {"date": "1 Jan 2020", "edition": "01 January 2020", "cat": "Politics",
         "title": "Old story", "summary": "old", "panel": "oldpanel"},
    ]
    merged = effective_archive(edition, prior)
    today_label = edition.meta.edition_label
    today = [it for it in merged if it["edition"] == today_label]
    older = [it for it in merged if it["edition"] != today_label]
    assert today, "today's items should be present"
    assert all("panel" not in it for it in older), "stale panels must be stripped"
    assert any("panel" in it for it in today), "current stories keep their panel"


def test_merge_dedupes_by_edition_and_title(edition):
    first = edition.archive[0].model_dump(exclude_none=True)
    merged = effective_archive(edition, [first])  # same item supplied as 'prior'
    keys = [(it["edition"], it["title"]) for it in merged]
    assert len(keys) == len(set(keys)), "merge must not duplicate (edition, title)"


def test_check_edition_cli_accepts_example():
    rc = check_edition.main([str(ROOT / "content" / "edition.example.json")])
    assert rc == 0


def test_check_edition_cli_rejects_missing_file(tmp_path):
    rc = check_edition.main([str(tmp_path / "nope.json")])
    assert rc == 2


def test_staleness_warns_on_carried_over_weather_and_markets(edition, tmp_path, monkeypatch):
    """Two dated editions sharing weather/markets should trigger warnings."""
    from build import render as r

    eds = tmp_path / "editions"
    eds.mkdir()
    (eds / "2026-06-20.json").write_text(edition.model_dump_json(), encoding="utf-8")
    cur = eds / "2026-06-21.json"
    cur.write_text(edition.model_dump_json(), encoding="utf-8")  # identical data

    monkeypatch.setattr(r, "EDITIONS", eds)
    warns = r._staleness_warnings(edition, cur)
    assert any("weather hourly" in w for w in warns)
    assert any("index strip" in w for w in warns)


def test_no_staleness_warning_for_first_edition(edition, tmp_path, monkeypatch):
    from build import render as r

    eds = tmp_path / "editions"
    eds.mkdir()
    cur = eds / "2026-06-21.json"
    cur.write_text(edition.model_dump_json(), encoding="utf-8")
    monkeypatch.setattr(r, "EDITIONS", eds)
    assert r._staleness_warnings(edition, cur) == []
