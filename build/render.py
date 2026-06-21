"""Render an Edition into the published static site.

Pipeline:  edition.json  ->  Jinja(base.html.j2 + assets)  ->  index.html
                                                              +  archive.json
                                                              +  template-reference.html
                                                              +  sitemap.xml (lastmod)
                                                              +  README.md edition block

A build-time validation gate (`build.validate`) runs against the rendered HTML;
if it reports any error the build FAILS and nothing is written.

Usage:
    python -m build.render                         # newest edition in content/editions
    python -m build.render --edition path/to.json  # explicit
    python -m build.render --check-only            # render+validate, write nothing
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from evenbrief.schema import Edition  # noqa: E402
from build.inline import load_assets  # noqa: E402
from build import validate as gate  # noqa: E402

SITE_URL = "https://owenautosport.github.io/Even-Brief/"
TEMPLATES = ROOT / "templates"
EDITIONS = ROOT / "content" / "editions"


# --------------------------------------------------------------------------- #
# Context assembly
# --------------------------------------------------------------------------- #
def effective_archive(edition: Edition, prior: list[dict] | None = None) -> list[dict]:
    """Merge today's archive items ahead of the existing archive, deduped.

    The edition only needs to carry *today's* items in ``edition.archive``; this
    folds in the prior ``archive.json`` so a hand-authored (Claude Code) edition
    doesn't have to re-state the whole history. Carried-over items lose their
    ``panel`` (those panels no longer exist in the new page); current-edition
    items keep theirs so the archive can open them in full. Dedupe key is
    (edition, title); the first occurrence (today's) wins.
    """
    label = edition.meta.edition_label
    seen: set[tuple[str, str]] = set()
    out: list[dict] = []

    def add(d: dict, is_today: bool) -> None:
        key = (d.get("edition", ""), (d.get("title") or "").strip().lower())
        if key in seen:
            return
        seen.add(key)
        d = dict(d)
        if not is_today:
            d.pop("panel", None)
        out.append(d)

    for it in edition.archive:
        add(it.model_dump(exclude_none=True), it.edition == label)
    for it in (prior or []):
        add(it, it.get("edition") == label)
    return out


def _archive_json(items: list[dict]) -> str:
    """One archive item per line, matching the reference's embedded layout."""
    body = ",\n".join(json.dumps(it, ensure_ascii=False) for it in items)
    return "[\n" + body + "\n]"


def _wx_json(edition: Edition) -> str:
    w = edition.weather
    payload = {
        "temp": w.hourly_temp,
        "precip": w.hourly_precip,
        "days": [d.model_dump() for d in w.days],
    }
    return json.dumps(payload, ensure_ascii=False)


def _seo(edition: Edition) -> dict:
    heads = [s.headline for s in edition.stories[:3]]
    desc = " · ".join(heads)
    if len(desc) > 200:
        desc = desc[:197].rstrip() + "…"
    return {
        "title": f"Even Brief — {edition.meta.date_display}",
        "description": desc,
        "url": SITE_URL,
        "og_image": SITE_URL + "og-image.png",
    }


def _jsonld(edition: Edition, seo: dict) -> str:
    lead = edition.stories[0]
    doc = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": lead.headline,
        "description": seo["description"],
        "datePublished": edition.meta.date_iso,
        "dateModified": edition.meta.date_iso,
        "image": [seo["og_image"]],
        "url": seo["url"],
        "isAccessibleForFree": True,
        "publisher": {
            "@type": "Organization",
            "name": "Even Brief",
            "logo": {"@type": "ImageObject", "url": SITE_URL + "apple-touch-icon.png"},
        },
        "author": {"@type": "Organization", "name": "Even Brief (AI-compiled)"},
    }
    return json.dumps(doc, ensure_ascii=False)


def render_html(edition: Edition, archive_items: list[dict] | None = None) -> str:
    """Render the page. ``archive_items`` is the merged archive to embed; if
    omitted, the edition's own archive list is used (used by the tests)."""
    if archive_items is None:
        archive_items = [it.model_dump(exclude_none=True) for it in edition.archive]
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(["html", "j2"], default_for_string=True),
        trim_blocks=False,
        lstrip_blocks=False,
    )
    seo = _seo(edition)
    ctx = {
        "meta": edition.meta,
        "weather": edition.weather,
        "headlines": edition.headlines,
        "stories": edition.stories,
        "markets": edition.markets,
        "archive_json": _archive_json(archive_items),
        "wx_json": _wx_json(edition),
        "seo": seo,
        "jsonld": _jsonld(edition, seo),
        **load_assets(),
    }
    return env.get_template("base.html.j2").render(**ctx) + "\n"


# --------------------------------------------------------------------------- #
# Side outputs
# --------------------------------------------------------------------------- #
def _update_sitemap(date_iso: str) -> None:
    p = ROOT / "sitemap.xml"
    if not p.exists():
        return
    import re
    txt = p.read_text(encoding="utf-8")
    txt = re.sub(r"<lastmod>[^<]*</lastmod>", f"<lastmod>{date_iso}</lastmod>", txt)
    p.write_text(txt, encoding="utf-8")


def _update_readme(edition: Edition) -> None:
    p = ROOT / "README.md"
    if not p.exists():
        return
    txt = p.read_text(encoding="utf-8")
    start, end = "<!--EDITION:START-->", "<!--EDITION:END-->"
    bullets = "\n".join(
        f"- **{s.headline}** — {s.summary}" for s in edition.stories
    )
    block = (
        f"{start}\n"
        f"## Current edition — {edition.meta.date_display}\n\n"
        f"Today's Top Headlines:\n\n"
        f"{bullets}\n\n"
        f"Read the live site: {SITE_URL}\n"
        f"{end}"
    )
    if start in txt and end in txt:
        import re
        txt = re.sub(
            re.escape(start) + r".*?" + re.escape(end),
            block.replace("\\", "\\\\"),
            txt,
            flags=re.DOTALL,
        )
    else:  # add markers just after the first paragraph block if missing
        txt = txt.rstrip() + "\n\n" + block + "\n"
    p.write_text(txt, encoding="utf-8")


def _load_prior_archive() -> list[dict]:
    p = ROOT / "archive.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def _newest_edition() -> Path:
    candidates = sorted(EDITIONS.glob("*.json"))
    if not candidates:
        raise SystemExit("no edition files in content/editions/")
    # Prefer date-named files; fall back to mtime.
    dated = [c for c in candidates if c.stem[:4].isdigit()]
    return (max(dated) if dated else max(candidates, key=lambda p: p.stat().st_mtime))


def _staleness_warnings(edition: Edition, edition_path: Path) -> list[str]:
    """Warn (non-fatal) if weather/markets look carried over from a prior edition.

    Catches the 'forgot to re-research the live sections' failure mode: if the new
    edition's hourly weather, masthead temp or index strip are byte-identical to
    the most recent *other* edition, that almost certainly means stale data.
    """
    others = sorted(
        p for p in EDITIONS.glob("*.json")
        if p.resolve() != edition_path.resolve() and p.stem[:4].isdigit()
    )
    if not others:
        return []
    try:
        prev = Edition.model_validate_json(others[-1].read_text(encoding="utf-8"))
    except Exception:
        return []
    warns: list[str] = []
    w, pw = edition.weather, prev.weather
    if w.hourly_temp == pw.hourly_temp and w.hourly_precip == pw.hourly_precip:
        warns.append(f"weather hourly temp/precip identical to {others[-1].name} — refresh today's weather?")
    if w.masthead.temp == pw.masthead.temp and w.masthead.cond == pw.masthead.cond:
        warns.append(f"masthead weather identical to {others[-1].name} — refresh today's weather?")
    if [i.model_dump() for i in edition.markets.movers.indices] == \
       [i.model_dump() for i in prev.markets.movers.indices]:
        warns.append(f"markets index strip identical to {others[-1].name} — refresh today's figures?")
    return warns


def build(edition_path: Path, check_only: bool = False) -> int:
    edition = Edition.model_validate_json(edition_path.read_text(encoding="utf-8"))
    for w in _staleness_warnings(edition, edition_path):
        print(f"  ⚠ staleness: {w}", file=sys.stderr)
    prior = _load_prior_archive()
    merged = effective_archive(edition, prior)
    html = render_html(edition, archive_items=merged)

    errors = gate.validate_edition(edition, html, prior_archive=prior)
    if errors:
        print("BUILD FAILED — validation gate rejected the edition:", file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        return 1

    if check_only:
        print(f"OK: edition '{edition.meta.edition_label}' renders and passes validation "
              f"({len(html)} bytes, {len(edition.stories)} stories, "
              f"{len(merged)} archive items after merge).")
        return 0

    (ROOT / "index.html").write_text(html, encoding="utf-8")
    (ROOT / "template-reference.html").write_text(html, encoding="utf-8")
    (ROOT / "archive.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=0) + "\n", encoding="utf-8",
    )
    _update_sitemap(edition.meta.date_iso)
    _update_readme(edition)
    print(f"Built index.html ({len(html)} bytes) + archive.json "
          f"({len(merged)} items) for {edition.meta.edition_label}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render an Even Brief edition to the static site.")
    ap.add_argument("--edition", type=Path, help="path to an edition JSON (default: newest)")
    ap.add_argument("--check-only", action="store_true", help="render + validate, write nothing")
    args = ap.parse_args(argv)
    path = args.edition or _newest_edition()
    return build(path, check_only=args.check_only)


if __name__ == "__main__":
    raise SystemExit(main())
