"""Schema validity + offline pipeline contract."""
from __future__ import annotations

import json

from evenbrief.schema import Edition


def test_dryrun_edition_validates(edition):
    assert isinstance(edition, Edition)
    assert edition.stories, "edition has no stories"
    assert len(edition.weather.hourly_temp) == 24
    assert len(edition.weather.hourly_precip) == 24
    assert edition.markets.overview.sources(), "markets overview needs sources"


def test_every_story_has_sources(edition):
    for s in edition.stories:
        assert s.sources(), f"story {s.id} has no sources"


def test_edition_round_trips(edition):
    data = edition.model_dump_json()
    again = Edition.model_validate_json(data)
    assert again.meta.edition_label == edition.meta.edition_label


def test_archive_items_unique(edition):
    seen = set()
    for it in edition.archive:
        key = (it.edition, it.title.strip().lower())
        assert key not in seen, f"duplicate archive item {it.title!r}"
        seen.add(key)


def test_json_schema_emits():
    schema = Edition.model_json_schema()
    assert schema["title"] == "Edition"
    # ensure it serialises (catches non-serialisable defaults)
    json.dumps(schema)
