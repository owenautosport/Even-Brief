"""Build-time validation gate.

`validate_edition` runs the accuracy + integrity checks the spec requires and
returns a list of error strings. A non-empty list means the build must FAIL and
nothing is committed:

  * HTML parses and the key components / selectors are present
  * the canonical palette is intact (design parity)
  * the embedded archive JSON is valid and de-duplicated
  * every story carries at least one source
  * every image URL is on the public-domain / open-licence host allowlist
  * no story duplicates an *older* archive edition (24-hour / dedupe rule)

`design_parity_errors` is also used directly by the test-suite against the
rendered output.
"""
from __future__ import annotations

import json
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# Hosts permitted for lead/hero images: public-domain or open-licensed sources.
ALLOWED_IMAGE_HOST_SUFFIXES = (
    "commons.wikimedia.org",
    "upload.wikimedia.org",
    "nasa.gov",
    "usgs.gov",
    "cdc.gov",
    "noaa.gov",
    "esa.int",
    "openverse.org",
    "wikimedia.org",
)

# Selectors / markers that must survive every render (design + behaviour parity).
REQUIRED_SELECTORS = [
    "header.masthead",
    "div.topbar",
    "aside#drawer",
    "section#headlines.panel.active",
    "section#markets",
    "section#movers",
    "section#calendar",
    "section#forecast",
    "section#stocks",
    "section#archive",
    "section#guide",
    "script#archiveData",
    "script#wxData",
    "#wxTempMini",
    "#fcRadar",
    ".confidence",
    ".timeline",
    ".themer",
    "#focusToggle",
]

# Canonical CSS custom properties that must appear unchanged in the stylesheet.
REQUIRED_PALETTE = {
    "--bg:#0c0d11",
    "--gold:#cda349",
    "--red:#e0414f",
    "--green:#48c78e",
    "--panel:#15171d",
}


def _host_ok(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == s or host.endswith("." + s) for s in ALLOWED_IMAGE_HOST_SUFFIXES)


def design_parity_errors(html: str) -> list[str]:
    """Structural + palette checks on the rendered HTML string."""
    errors: list[str] = []
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:  # pragma: no cover - parser is very tolerant
        return [f"HTML failed to parse: {exc}"]

    if not soup.find("html"):
        errors.append("no <html> root element")
    for sel in REQUIRED_SELECTORS:
        if soup.select_one(sel) is None:
            errors.append(f"missing required selector: {sel}")

    # Palette parity: every canonical token must be present verbatim.
    style = soup.find("style")
    css = style.text if style else ""
    for token in REQUIRED_PALETTE:
        if token not in css.replace(" ", ""):
            errors.append(f"palette drift: missing CSS token {token}")

    # Theme + focus wiring (light theme + focus-off must be in the app JS).
    script_text = "\n".join(s.text for s in soup.find_all("script"))
    if "data-theme" not in script_text:
        errors.append("theme switching (data-theme) not wired in JS")
    if "setFocus(false)" not in script_text:
        errors.append("focus mode default-off not wired in JS")

    # Leaflet + TradingView must remain present (client-side, online-only).
    if "leaflet" not in html:
        errors.append("Leaflet radar assets missing")
    if "tradingview" not in html.lower():
        errors.append("TradingView widgets missing")

    # Embedded archive JSON must parse.
    arch = soup.find("script", id="archiveData")
    if arch is None or not arch.text.strip():
        errors.append("archiveData island missing or empty")
    else:
        try:
            json.loads(arch.text)
        except json.JSONDecodeError as exc:
            errors.append(f"archiveData is not valid JSON: {exc}")

    # wxData island must parse and carry the three daily arrays.
    wx = soup.find("script", id="wxData")
    if wx is None or not wx.text.strip():
        errors.append("wxData island missing or empty")
    else:
        try:
            d = json.loads(wx.text)
            for key in ("temp", "precip", "days"):
                if key not in d:
                    errors.append(f"wxData missing '{key}'")
        except json.JSONDecodeError as exc:
            errors.append(f"wxData is not valid JSON: {exc}")

    return errors


def validate_edition(edition, html: str, prior_archive: list[dict] | None = None) -> list[str]:
    """Full gate: structural parity + content-accuracy invariants.

    `edition` is a schema.Edition; `html` the rendered page; `prior_archive`
    the archive.json contents from *before* this edition (for the dedupe rule).
    """
    errors = list(design_parity_errors(html))

    # Every story (and the markets overview) needs at least one source.
    panels = list(edition.stories) + [edition.markets.overview]
    for s in panels:
        if not s.sources():
            errors.append(f"story '{s.id}' has no sources")

    # Image URLs must be on the licence-safe allowlist.
    for s in panels:
        if s.image and not _host_ok(s.image.url):
            errors.append(f"story '{s.id}' image is not on an open-licence host: {s.image.url}")

    # 24-hour / dedupe rule: a current story must not repeat an OLDER archive
    # edition's headline verbatim (a genuine new development must be rewritten).
    if prior_archive:
        prior_titles = {
            (it.get("title") or "").strip().lower()
            for it in prior_archive
            if it.get("edition") != edition.meta.edition_label
        }
        for s in edition.stories:
            if s.headline.strip().lower() in prior_titles:
                errors.append(f"story '{s.id}' duplicates an earlier archive headline (24h/dedupe rule)")

    # The embedded archive must not contain duplicate (edition, title) pairs.
    seen: set[tuple[str, str]] = set()
    for it in edition.archive:
        key = (it.edition, it.title.strip().lower())
        if key in seen:
            errors.append(f"duplicate archive entry: {it.title!r} in {it.edition}")
        seen.add(key)

    return errors
