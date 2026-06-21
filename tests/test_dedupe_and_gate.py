"""The validation gate must FAIL on malformed editions (accuracy guardrails)."""
from __future__ import annotations

import copy

from build import validate as gate
from evenbrief.schema import ArchiveItem, Edition, Source


def _clone(edition) -> Edition:
    return Edition.model_validate(copy.deepcopy(edition.model_dump()))


def test_duplicate_archive_entry_is_rejected(edition, rendered_html):
    bad = _clone(edition)
    first = bad.archive[0]
    bad.archive.append(ArchiveItem(date=first.date, edition=first.edition,
                                   cat=first.cat, title=first.title, summary=first.summary))
    errors = gate.validate_edition(bad, rendered_html, prior_archive=[])
    assert any("duplicate archive entry" in e for e in errors)


def test_24h_dedupe_rule_rejects_reposted_headline(edition, rendered_html):
    prior = [{"edition": "01 January 2020", "title": edition.stories[0].headline,
              "date": "1 Jan 2020", "cat": "Politics", "summary": "old"}]
    errors = gate.validate_edition(edition, rendered_html, prior_archive=prior)
    assert any("24h/dedupe" in e for e in errors)


def test_story_without_sources_is_rejected(edition, rendered_html):
    bad = _clone(edition)
    bad.stories[0].sidebar_blocks = [
        b for b in bad.stories[0].sidebar_blocks if b.type != "sources"
    ]
    errors = gate.validate_edition(bad, rendered_html, prior_archive=[])
    assert any("no sources" in e for e in errors)


def test_non_open_licence_image_is_rejected(edition, rendered_html):
    bad = _clone(edition)
    img = bad.stories[0].image
    if img is None:
        from evenbrief.schema import Image
        bad.stories[0].image = Image(url="https://www.reuters.com/photo.jpg", alt="x")
    else:
        img.url = "https://www.reuters.com/photo.jpg"
    errors = gate.validate_edition(bad, rendered_html, prior_archive=[])
    assert any("open-licence host" in e for e in errors)


def test_broken_html_fails_parity():
    errors = gate.design_parity_errors("<html><body>nothing here</body></html>")
    assert errors, "a page missing every component should fail parity"
