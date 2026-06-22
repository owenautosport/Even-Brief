"""The Even Brief content contract.

These Pydantic models define what a validated *edition* is. The generation
pipeline produces an ``Edition``; the build step renders it. Everything in
between is plain data - no HTML lives here.

Design notes
------------
* An article is an **ordered list of blocks** (``article_blocks``) plus an
  ordered list of **sidebar blocks** (``sidebar_blocks``). This mirrors the
  reference, where a timeline, pull-quote or media-framing section can appear
  at any point in the prose, and the framing box lives in the article on some
  stories and in the sidebar rail on others.
* "HTML-bearing" string fields (paragraph bodies, key-fact bullets, logic
  flags) permit the small inline tags the reference uses (``<strong>``,
  ``<em>``, ``<span class="followup">``). They are emitted with Jinja's
  ``| safe`` and so MUST be producer-trusted; the validator (``validate.py``)
  enforces that every story carries sources and that image URLs are on the
  licence-safe allowlist.
* ``confidence.level`` maps 1:1 to the reference CSS classes
  (``cf-corrob`` / ``cf-develop`` / ``cf-disputed``).
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

# Categories drive badge colours, placeholder tiles and archive filtering.
Category = Literal[
    "Politics", "Conflict", "Business", "Markets", "Health",
    "Science", "Technology", "Climate", "Sport",
]
ConfidenceLevel = Literal["corrob", "develop", "disputed"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Shared value objects
# --------------------------------------------------------------------------- #
class Image(_Model):
    """A licence-safe lead/hero image.

    ``url`` must be public-domain or open-licensed; ``validate.py`` enforces the
    host allowlist (Wikimedia Commons / Openverse / NASA / USGS / CDC ...).
    """
    url: str
    alt: str
    caption: str = ""        # shown as <figcaption>, e.g. "Photo: NASA - public domain"
    credit: str = ""         # attribution string (for provenance records)
    license: str = ""        # e.g. "public domain", "CC BY-SA 3.0"


class Source(_Model):
    outlet: str
    title: str
    url: str
    lean: str = ""           # editorial bias note for the framing bar, e.g. "Lean Left"


class Confidence(_Model):
    level: ConfidenceLevel
    label: str               # "Verified" / "Developing" / "Disputed"
    why: str                 # the "- ..." trailing clause


class Badge(_Model):
    label: str               # e.g. "Politics", "Conflict"
    cls: str                 # CSS modifier, e.g. "b-politics"


# --------------------------------------------------------------------------- #
# Article blocks (ordered, rendered inside .article)
# --------------------------------------------------------------------------- #
class Paragraph(_Model):
    type: Literal["p"] = "p"
    html: str                # may contain <strong>/<em>/<span class="followup">


class PullQuote(_Model):
    type: Literal["pullquote"] = "pullquote"
    text: str
    src: str = ""            # dated attribution, e.g. "- Swiss FM, 20 June 2026"


class TimelineEvent(_Model):
    date: str                # ISO yyyy-mm-dd (data-date; drives auto gap labels)
    label: str               # display date, e.g. "17 Jun"
    title: str
    detail: str


class Timeline(_Model):
    type: Literal["timeline"] = "timeline"
    head: str = "Timeline"
    sub: str = "Tap an event to expand. Spacing reflects the time between events."
    note: str = ""
    events: list[TimelineEvent] = Field(min_length=2)


class BiasSegment(_Model):
    lean: str                # "Left" / "Centre" / "Right"
    pct: int = Field(ge=0, le=100)
    color: str               # hex, e.g. "#3b82c4"


class Framing(_Model):
    type: Literal["framing"] = "framing"
    overview: str            # the "<strong>Political-bias overview:</strong> ..." text
    bias: list[BiasSegment] = Field(min_length=1)
    caption: str = "Share of the gathered sources by lean - an approximate read, not a measure of the entire press."
    ratings_html: str = ""   # the "Source leans: ..." line (allows <b>/<a>)
    lines: list[str] = Field(default_factory=list)  # framing paragraphs (HTML w/ <span class="lean">)


ArticleBlock = Annotated[
    Union[Paragraph, PullQuote, Timeline, Framing],
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------- #
# Sidebar blocks (ordered, rendered inside .side)
# --------------------------------------------------------------------------- #
class KeyFacts(_Model):
    type: Literal["keyfacts"] = "keyfacts"
    items: list[str] = Field(min_length=1)   # HTML bullets


class Sources(_Model):
    type: Literal["sources"] = "sources"
    items: list[Source] = Field(min_length=1)


class FactCheckItem(_Model):
    status: Literal["ok", "unv"]             # confirmed / unverified
    verdict: str                             # "Confirmed" / "Unverified"
    text: str


class FactCheck(_Model):
    type: Literal["factcheck"] = "factcheck"
    items: list[FactCheckItem] = Field(min_length=1)


class CommonGround(_Model):
    type: Literal["ground"] = "ground"
    agree: list[str] = Field(default_factory=list)
    contest: list[str] = Field(default_factory=list)


class LogicFlags(_Model):
    type: Literal["logic"] = "logic"
    items: list[str] = Field(min_length=1)   # numbered/explained flags (HTML)


SidebarBlock = Annotated[
    Union[KeyFacts, Sources, FactCheck, CommonGround, LogicFlags, Framing],
    Field(discriminator="type"),
]


# --------------------------------------------------------------------------- #
# Story
# --------------------------------------------------------------------------- #
class Story(_Model):
    id: str                  # slug used as panel id + nav data-target, e.g. "iran"
    nav_label: str           # drawer label, e.g. "Iran Nuclear Talks"
    category: Category
    badges: list[Badge] = Field(min_length=1)
    dateline: str            # e.g. "21 June 2026 | Geneva & Tehran"
    headline: str
    summary: str             # one-line, used by hero/cards/archive
    confidence: Confidence
    followup: bool = False
    image: Optional[Image] = None
    inline_image: Optional[Image] = None   # a second, different-but-relevant image floated mid-article
    article_blocks: list[ArticleBlock] = Field(min_length=1)
    sidebar_blocks: list[SidebarBlock] = Field(default_factory=list)

    def sources(self) -> list[Source]:
        out: list[Source] = []
        for b in self.sidebar_blocks:
            if isinstance(b, Sources):
                out.extend(b.items)
        return out


# --------------------------------------------------------------------------- #
# Headlines (BBC-style landing grid)
# --------------------------------------------------------------------------- #
class HeadlineCard(_Model):
    target: str              # panel id to open
    badge: Badge
    cat_cls: str             # placeholder-tile class, e.g. "cat-politics"
    emoji: str               # placeholder glyph, e.g. "🏛"
    headline: str
    summary: str
    image_url: Optional[str] = None
    lead: bool = False       # True for the hero card


class Headlines(_Model):
    hero: HeadlineCard
    cards: list[HeadlineCard] = Field(min_length=1)


# --------------------------------------------------------------------------- #
# Markets
# --------------------------------------------------------------------------- #
class IndexCard(_Model):
    name: str
    value: str
    change: str              # e.g. "▲ 1.08%"
    direction: Literal["up", "down"]


class MoverRow(_Model):
    ticker: str
    name: str
    pct: str                 # e.g. "+55.87%"
    direction: Literal["up", "down"]


class MoverBox(_Model):
    kind: Literal["gain", "lose"]
    heading: str             # e.g. "▲ Top gainers"
    region_note: str         # e.g. "US · Thu close"
    rows: list[MoverRow] = Field(min_length=1)


class MoversBlock(_Model):
    """A region group on the Movers dashboard (US / UK / Europe ...)."""
    section: str             # e.g. "United States - top movers"
    boxes: list[MoverBox] = Field(min_length=1)
    note_html: str = ""      # trailing context note


class Movers(_Model):
    dateline: str
    headline: str
    note_html: str           # the "Markets are closed ..." disclosure
    indices: list[IndexCard] = Field(min_length=1)
    groups: list[MoversBlock] = Field(default_factory=list)
    sources: list[Source] = Field(min_length=1)


class CalItem(_Model):
    chip: Literal["data", "bank", "earn", "ipo", "div"]
    chip_label: str          # "Data" / "Central bank" / ...
    event: str
    meta: str = ""
    done: str = ""           # e.g. "✓ released" (empty for upcoming)


class CalDay(_Model):
    day: str                 # e.g. "24" or "16-17"
    month: str               # e.g. "Jun"
    dow: str                 # e.g. "Wed"
    state: Literal["past", "next", ""] = ""
    items: list[CalItem] = Field(min_length=1)


class Calendar(_Model):
    dateline: str
    headline: str
    note_html: str
    days: list[CalDay] = Field(min_length=1)
    sources: list[Source] = Field(min_length=1)


class Markets(_Model):
    # Overview is a full story-like panel (article + rail), rendered by the same macro.
    overview: Story
    movers: Movers
    calendar: Calendar


# --------------------------------------------------------------------------- #
# Weather
# --------------------------------------------------------------------------- #
class MastheadWeather(_Model):
    loc: str = "Guildford, UK"
    temp: str                # e.g. "25°C"
    cond: str                # e.g. "Warm & humid · sunny spells"
    low: str                 # e.g. "↓ Low 17°C"
    rain: str                # e.g. "Rain <5%"
    gusts: str               # e.g. "Gusts 24 mph"


class WarnCard(_Model):
    sev: Literal["amber", "yellow", "red", "none"]
    sev_label: str           # "Amber" / "Yellow" ...
    title: str
    body_html: str


class WeatherDay(_Model):
    d: str                   # "Sun 21"
    ic: str                  # emoji icon
    cond: str
    hi: int
    lo: int
    feels: int
    wind: int
    gust: int
    hum: int
    uv: int
    pc: int                  # precip chance %
    mm: float                # precip mm
    sr: str                  # sunrise "04:43"
    ss: str                  # sunset
    warn: bool = False
    tag: str                 # short label on tile, e.g. "5% rain"
    sum: str                 # one-line summary in detail panel


class Weather(_Model):
    masthead: MastheadWeather
    current_temp: str        # forecast-page big number, e.g. "25°C"
    current_cond: str
    current_meta: str        # "Feels like 26°C · Low 17°C ..."
    warnings: list[WarnCard] = Field(default_factory=list)
    hourly_temp: list[int] = Field(min_length=24, max_length=24)
    hourly_precip: list[int] = Field(min_length=24, max_length=24)
    days: list[WeatherDay] = Field(min_length=1)
    sources: list[Source] = Field(min_length=1)


# --------------------------------------------------------------------------- #
# Archive
# --------------------------------------------------------------------------- #
class ArchiveItem(_Model):
    date: str                # "21 Jun 2026"
    edition: str             # "21 June 2026"
    cat: Category
    title: str
    summary: str
    panel: Optional[str] = None   # set only for the current edition's stories


# --------------------------------------------------------------------------- #
# Edition (top level)
# --------------------------------------------------------------------------- #
class Meta(_Model):
    date_iso: str            # "2026-06-21"
    date_display: str        # "Sunday, 21 June 2026"
    edition_label: str       # "21 June 2026" (matches archive `edition`)
    compile_time: str        # "10:50 BST" - single real London time, never a range
    location: str = "London"
    kicker: str = "Investigative Global Edition"


class Edition(_Model):
    """One day's validated briefing - the complete render input."""
    meta: Meta
    weather: Weather
    headlines: Headlines
    stories: list[Story] = Field(min_length=1)
    markets: Markets
    archive: list[ArchiveItem] = Field(min_length=1)

    def top_headline_panels(self) -> list[str]:
        return [s.id for s in self.stories]


def json_schema() -> dict:
    """Return the JSON Schema for an Edition (used by tests + the build gate)."""
    return Edition.model_json_schema()
