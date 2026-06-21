"""Render-output checks: validation gate, design parity, asset fidelity."""
from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from build import validate as gate

ROOT = Path(__file__).resolve().parent.parent


def test_gate_passes_on_dryrun(edition, rendered_html):
    errors = gate.validate_edition(edition, rendered_html, prior_archive=[])
    assert errors == [], f"validation gate reported: {errors}"


def test_required_components_present(rendered_html):
    assert gate.design_parity_errors(rendered_html) == []


def test_no_unrendered_template_tokens(rendered_html):
    assert "{{" not in rendered_html and "{%" not in rendered_html


def test_html_parses_and_has_panels(rendered_html):
    soup = BeautifulSoup(rendered_html, "html.parser")
    assert soup.find("html") is not None
    assert soup.title and "Even Brief" in soup.title.string
    # headlines, markets, movers, calendar, forecast, stocks, archive, guide + stories
    assert len(soup.select("section.panel")) >= 8


def test_data_islands_valid_json(rendered_html):
    soup = BeautifulSoup(rendered_html, "html.parser")
    wx = json.loads(soup.find("script", id="wxData").string)
    assert len(wx["temp"]) == 24 and len(wx["precip"]) == 24 and wx["days"]
    arch = json.loads(soup.find("script", id="archiveData").string)
    assert isinstance(arch, list) and arch


def test_seo_and_jsonld_present(rendered_html):
    soup = BeautifulSoup(rendered_html, "html.parser")
    assert soup.find("meta", attrs={"name": "description"})
    assert soup.find("meta", property="og:image")
    ld = json.loads(soup.find("script", type="application/ld+json").string)
    assert ld["@type"] == "NewsArticle"


def test_assets_match_reference_verbatim():
    """The extracted CSS/JS must be byte-identical to the frozen reference."""
    ref = (ROOT / "reference" / "index.html").read_text(encoding="utf-8")
    css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
    # CSS is lifted verbatim from the single <style> block.
    style_inner = ref.split("<style>", 1)[1].split("</style>", 1)[0]
    assert css.strip("\n") == style_inner.strip("\n")


def test_app_js_is_data_driven_not_hardcoded():
    """app.js must read weather content from the data island, not embed it."""
    js = (ROOT / "assets" / "app.js").read_text(encoding="utf-8")
    assert "wxData" in js, "app.js should read the wxData island"
    assert "var DAYS=(__wx.days" in js, "DAYS literal should be lifted to data"
    # the long hardcoded literal must be gone
    assert "{d:'Sun 21'" not in js


def test_palette_tokens_intact():
    css = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8").replace(" ", "")
    for token in ("--bg:#0c0d11", "--gold:#cda349", "--red:#e0414f", "--green:#48c78e"):
        assert token in css, f"canonical palette token missing: {token}"
