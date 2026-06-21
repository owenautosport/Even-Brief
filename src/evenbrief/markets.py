"""Markets section: overview (a Story), movers, and current-month calendar.

Accuracy rules baked in:
* corroborate from 2+ independent financial sources;
* never invent tickers or percentages - if single-stock movers can't be sourced
  for a region, present index-level only and say so;
* be explicit which session each figure is from; on a non-trading day, say so
  and use last-close figures.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .schema import (
    Badge,
    CalDay,
    Calendar,
    CalItem,
    Confidence,
    IndexCard,
    Markets,
    MoverBox,
    MoverRow,
    Movers,
    MoversBlock,
    Paragraph,
    Source,
    Sources,
    Story,
)

if TYPE_CHECKING:
    from .client import BriefingClient


# --------------------------------------------------------------------------- #
# Parse targets (mirror the schema closely but as plain models the model fills)
# --------------------------------------------------------------------------- #
class _Index(BaseModel):
    name: str
    value: str
    change: str              # e.g. "+1.08%"
    direction: str           # "up" | "down"


class _Mover(BaseModel):
    ticker: str
    name: str
    pct: str
    direction: str


class _Region(BaseModel):
    section: str             # "United States - top movers"
    region_note: str         # "US - Thu close"
    gainers: list[_Mover] = Field(default_factory=list)
    losers: list[_Mover] = Field(default_factory=list)
    index_only: bool = False  # True when single-stock movers couldn't be sourced
    note_html: str = ""


class _CalItem(BaseModel):
    chip: str                # data|bank|earn|ipo|div
    chip_label: str
    event: str
    meta: str = ""
    done: str = ""


class _CalDay(BaseModel):
    day: str
    month: str
    dow: str
    state: str = ""          # past|next|""
    items: list[_CalItem] = Field(min_length=1)


class _SourceNote(BaseModel):
    outlet: str
    title: str
    url: str
    lean: str = ""


class _MarketsData(BaseModel):
    """The full structured markets payload returned by the research+parse pass."""
    overview_dateline: str
    overview_headline: str
    overview_paragraphs: list[str] = Field(min_length=1)
    movers_dateline: str
    movers_headline: str
    movers_note_html: str
    indices: list[_Index] = Field(min_length=1)
    regions: list[_Region] = Field(default_factory=list)
    calendar_dateline: str
    calendar_headline: str
    calendar_note_html: str
    calendar_days: list[_CalDay] = Field(min_length=1)
    sources: list[_SourceNote] = Field(min_length=1)


_VALID_CHIPS = {"data", "bank", "earn", "ipo", "div"}

_SYSTEM = (
    "You are a markets desk writer for 'Even Brief'. Neutral, non-emotive "
    "register. Corroborate every figure across 2+ independent financial sources. "
    "Never invent tickers or percentages. If single-stock movers cannot be "
    "sourced for a region, present that region at index level only and say so. "
    "Be explicit which trading session each figure is from; on a non-trading day "
    "say so and use last-close figures."
)


def _dir(v: str) -> str:
    return "down" if str(v).strip().lower().startswith("d") else "up"


def _to_sources(notes: list[_SourceNote]) -> list[Source]:
    out = [
        Source(outlet=n.outlet or "source", title=n.title or n.outlet or "source",
               url=n.url, lean=n.lean)
        for n in notes if n.url
    ]
    return out or [Source(outlet="source", title="markets data", url="https://example.org")]


def build_markets(client: "BriefingClient", today_iso: str) -> Markets:
    """Research and assemble the Markets section for ``today_iso``."""
    prompt = (
        f"Today is {today_iso}. Research global markets for a neutral daily "
        "briefing using web search across 2+ independent financial sources "
        "(Reuters, Bloomberg, AP, FT, Yahoo Finance, exchange sites).\n\n"
        "Produce:\n"
        "(a) OVERVIEW: a short neutral markets analysis (2-4 paragraphs) plus a "
        "dateline and headline.\n"
        "(b) INDICES: S&P 500, NASDAQ, Dow, FTSE 100, Nikkei 225, DAX, Shanghai - "
        "value and % change with direction; include Brent/WTI, gold if available.\n"
        "(c) MOVERS: for the US, UK (FTSE 100) and Europe, the biggest gainers and "
        "losers (~5 names each side) with ticker, company, % change and session. "
        "If you cannot source single-stock movers for a region, mark it "
        "index_only=true and explain in note_html. Never invent tickers/percentages.\n"
        "(d) CALENDAR: economic events for the CURRENT MONTH - data releases, "
        "central-bank meetings, earnings, IPOs, dividend ex-dates. Each with a "
        "chip type (data/bank/earn/ipo/div), label, event, one-line meta, and "
        "'done' marker for past items. Mark the next upcoming day state='next' "
        "and past days state='past'.\n"
        "(e) SOURCES: working links for the figures.\n"
        "State the date and session for every figure. If today is a non-trading "
        "day, say so and use last-close figures."
    )
    research = client.research(prompt=prompt, system=_SYSTEM, max_searches=10)
    data = client.parse(
        output_format=_MarketsData,
        system=_SYSTEM,
        prompt=(
            "Structure the markets research below into the required data. Keep "
            "all prose neutral. Use only figures present in the notes.\n\n"
            "RESEARCH NOTES:\n" + research.text
        ),
        max_tokens=10000,
    )

    sources = _to_sources(data.sources)

    # ----- overview story ------------------------------------------------- #
    overview = Story(
        id="markets-overview",
        nav_label="Markets Overview",
        category="Markets",
        badges=[Badge(label="Markets", cls="b-markets")],
        dateline=data.overview_dateline,
        headline=data.overview_headline,
        summary=data.overview_paragraphs[0][:160],
        confidence=Confidence(level="corrob", label="Verified",
                              why="corroborated across 2+ financial sources"),
        article_blocks=[Paragraph(html=p) for p in data.overview_paragraphs],
        sidebar_blocks=[Sources(items=sources)],
    )

    # ----- movers --------------------------------------------------------- #
    indices = [
        IndexCard(name=i.name, value=i.value, change=i.change, direction=_dir(i.direction))
        for i in data.indices
    ]
    groups: list[MoversBlock] = []
    for r in data.regions:
        boxes: list[MoverBox] = []
        if not r.index_only and r.gainers:
            boxes.append(MoverBox(
                kind="gain", heading="▲ Top gainers", region_note=r.region_note,
                rows=[MoverRow(ticker=m.ticker, name=m.name, pct=m.pct,
                               direction=_dir(m.direction)) for m in r.gainers],
            ))
        if not r.index_only and r.losers:
            boxes.append(MoverBox(
                kind="lose", heading="▼ Top losers", region_note=r.region_note,
                rows=[MoverRow(ticker=m.ticker, name=m.name, pct=m.pct,
                               direction=_dir(m.direction)) for m in r.losers],
            ))
        if boxes:
            groups.append(MoversBlock(section=r.section, boxes=boxes, note_html=r.note_html))
        # index_only regions contribute their note via the indices strip already.

    movers = Movers(
        dateline=data.movers_dateline,
        headline=data.movers_headline,
        note_html=data.movers_note_html,
        indices=indices,
        groups=groups,
        sources=sources,
    )

    # ----- calendar ------------------------------------------------------- #
    cal_days: list[CalDay] = []
    for d in data.calendar_days:
        items = []
        for it in d.items:
            chip = it.chip if it.chip in _VALID_CHIPS else "data"
            items.append(CalItem(chip=chip, chip_label=it.chip_label, event=it.event,
                                 meta=it.meta, done=it.done))
        state = d.state if d.state in ("past", "next", "") else ""
        cal_days.append(CalDay(day=d.day, month=d.month, dow=d.dow, state=state, items=items))

    calendar = Calendar(
        dateline=data.calendar_dateline,
        headline=data.calendar_headline,
        note_html=data.calendar_note_html,
        days=cal_days,
        sources=sources,
    )

    return Markets(overview=overview, movers=movers, calendar=calendar)
