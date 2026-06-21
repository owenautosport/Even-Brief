"""Built-in offline fixtures for ``--dry-run``.

These construct a fully schema-valid ``Edition`` with NO API calls and NO
``ANTHROPIC_API_KEY`` - this is what CI/tests use to prove the data contract and
the assembly path work end to end. The content is illustrative placeholder text
clearly written in the neutral register; it is not real news.
"""
from __future__ import annotations

from .schema import (
    Badge,
    BiasSegment,
    CalDay,
    Calendar,
    CalItem,
    CommonGround,
    Confidence,
    FactCheck,
    FactCheckItem,
    Framing,
    Image,
    IndexCard,
    KeyFacts,
    LogicFlags,
    MastheadWeather,
    Markets,
    Meta,
    MoverBox,
    MoverRow,
    Movers,
    MoversBlock,
    Paragraph,
    PullQuote,
    Source,
    Sources,
    Story,
    Timeline,
    TimelineEvent,
    WarnCard,
    Weather,
    WeatherDay,
)
from .assemble import assemble_edition


def _meta() -> Meta:
    return Meta(
        date_iso="2026-06-22",
        date_display="Monday, 22 June 2026",
        edition_label="22 June 2026",
        compile_time="06:30 BST",
        location="London",
        kicker="Investigative Global Edition",
    )


def _story_one() -> Story:
    return Story(
        id="sample-talks",
        nav_label="Sample Diplomatic Talks",
        category="Politics",
        badges=[Badge(label="Politics", cls="b-politics")],
        dateline="22 June 2026 | Geneva",
        headline="Negotiators meet for a further round of talks",
        summary="Officials from several governments met to continue discussions; no agreement was announced.",
        confidence=Confidence(level="corrob", label="Verified",
                              why="reported by multiple wire services"),
        image=Image(
            url="https://commons.wikimedia.org/wiki/Special:FilePath/Palais_des_Nations.jpg",
            alt="Exterior of a conference building",
            caption="Photo: Wikimedia Commons - public domain",
            credit="Wikimedia Commons",
            license="public domain",
        ),
        article_blocks=[
            Paragraph(html="Officials met on 22 June to continue talks, according to two news agencies."),
            Paragraph(html="A spokesperson said the discussions would continue."),
            PullQuote(text="The talks will continue tomorrow.",
                     src="-- Spokesperson, 22 June 2026"),
            Paragraph(html="No agreement was announced by the end of the day."),
            Timeline(
                events=[
                    TimelineEvent(date="2026-06-20", label="20 Jun",
                                 title="Talks announced", detail="The meeting was scheduled."),
                    TimelineEvent(date="2026-06-22", label="22 Jun",
                                 title="Talks held", detail="Officials met in Geneva."),
                ],
                note="Further sessions are expected.",
            ),
            Framing(
                overview="<strong>Political-bias overview:</strong> coverage drawn from wire and centre outlets.",
                bias=[
                    BiasSegment(lean="Left", pct=33, color="#3b82c4"),
                    BiasSegment(lean="Centre", pct=34, color="#9aa0ac"),
                    BiasSegment(lean="Right", pct=33, color="#c4513b"),
                ],
                lines=["Outlets across the spectrum reported the meeting similarly."],
            ),
        ],
        sidebar_blocks=[
            KeyFacts(items=["Talks held 22 June in Geneva", "No agreement announced"]),
            Sources(items=[
                Source(outlet="Reuters", title="Officials meet for talks",
                       url="https://www.reuters.com/", lean="Wire"),
                Source(outlet="AP", title="Negotiators continue discussions",
                       url="https://apnews.com/", lean="Wire"),
            ]),
            FactCheck(items=[
                FactCheckItem(status="ok", verdict="Confirmed",
                             text="Meeting took place on 22 June (Reuters, AP)."),
            ]),
            CommonGround(agree=["A meeting took place."],
                        contest=["Whether progress was made."]),
            LogicFlags(items=["1. Dates are internally consistent across sources."]),
        ],
    )


def _story_two() -> Story:
    return Story(
        id="sample-science",
        nav_label="Sample Research Finding",
        category="Science",
        badges=[Badge(label="Science", cls="b-science")],
        dateline="22 June 2026 | London",
        headline="Researchers publish a new study",
        summary="A peer-reviewed study reported findings on a sample dataset; the authors called for further work.",
        confidence=Confidence(level="develop", label="Developing",
                             why="single peer-reviewed study, awaiting replication"),
        article_blocks=[
            Paragraph(html="A study published on 22 June reported its findings."),
            Paragraph(html="The authors said further research was needed."),
        ],
        sidebar_blocks=[
            KeyFacts(items=["Study published 22 June"]),
            Sources(items=[
                Source(outlet="Nature", title="Study published",
                       url="https://www.nature.com/", lean="Centre"),
            ]),
            FactCheck(items=[
                FactCheckItem(status="unv", verdict="Unverified",
                             text="Findings rest on a single study (Nature)."),
            ]),
        ],
    )


def _markets() -> Markets:
    sources = [
        Source(outlet="Reuters", title="Markets wrap", url="https://www.reuters.com/markets/", lean="Wire"),
        Source(outlet="Bloomberg", title="Index levels", url="https://www.bloomberg.com/markets", lean="Centre"),
    ]
    overview = Story(
        id="markets-overview",
        nav_label="Markets Overview",
        category="Markets",
        badges=[Badge(label="Markets", cls="b-markets")],
        dateline="22 June 2026 | Global",
        headline="Indices closed mixed",
        summary="Major equity indices closed mixed on 22 June, according to two financial outlets.",
        confidence=Confidence(level="corrob", label="Verified",
                             why="figures corroborated across two financial sources"),
        article_blocks=[
            Paragraph(html="Major indices closed mixed on 22 June, per Reuters and Bloomberg."),
            Paragraph(html="Brent crude and gold were little changed."),
        ],
        sidebar_blocks=[Sources(items=sources)],
    )
    movers = Movers(
        dateline="22 June 2026",
        headline="Top movers",
        note_html="Figures reflect the previous regular session's close.",
        indices=[
            IndexCard(name="S&P 500", value="5,432.10", change="▲ 0.40%", direction="up"),
            IndexCard(name="FTSE 100", value="8,210.55", change="▼ 0.15%", direction="down"),
        ],
        groups=[
            MoversBlock(
                section="United States - top movers",
                boxes=[
                    MoverBox(kind="gain", heading="▲ Top gainers", region_note="US - prior close",
                             rows=[MoverRow(ticker="AAA", name="Sample Co", pct="+3.20%", direction="up")]),
                    MoverBox(kind="lose", heading="▼ Top losers", region_note="US - prior close",
                             rows=[MoverRow(ticker="BBB", name="Example Inc", pct="-2.10%", direction="down")]),
                ],
                note_html="Single-stock figures from the prior US close.",
            ),
        ],
        sources=sources,
    )
    calendar = Calendar(
        dateline="June 2026",
        headline="Economic calendar - June",
        note_html="Past items marked; the next event is highlighted.",
        days=[
            CalDay(day="20", month="Jun", dow="Sat", state="past",
                   items=[CalItem(chip="data", chip_label="Data", event="Sample data release",
                                  meta="placeholder", done="✓ released")]),
            CalDay(day="24", month="Jun", dow="Wed", state="next",
                   items=[CalItem(chip="bank", chip_label="Central bank", event="Sample rate decision",
                                  meta="placeholder")]),
        ],
        sources=sources,
    )
    return Markets(overview=overview, movers=movers, calendar=calendar)


def _weather() -> Weather:
    hourly_temp = [16, 16, 15, 15, 15, 16, 17, 18, 19, 20, 21, 22,
                   23, 24, 24, 24, 23, 22, 21, 20, 19, 18, 17, 17]
    hourly_precip = [5, 5, 5, 10, 10, 5, 5, 5, 0, 0, 0, 0,
                     5, 5, 10, 10, 15, 10, 5, 5, 5, 5, 5, 5]
    return Weather(
        masthead=MastheadWeather(
            temp="24°C", cond="Sunny spells", low="↓ Low 15°C",
            rain="Rain 10%", gusts="Gusts 22 mph",
        ),
        current_temp="24°C",
        current_cond="Sunny spells",
        current_meta="Feels like 24°C · Low 15°C · Rain 10%",
        warnings=[
            WarnCard(sev="yellow", sev_label="Yellow", title="Sample advisory",
                     body_html="Placeholder advisory text for the dry-run fixture."),
        ],
        hourly_temp=hourly_temp,
        hourly_precip=hourly_precip,
        days=[
            WeatherDay(d="Mon 22", ic="☀", cond="Sunny spells", hi=24, lo=15, feels=24,
                       wind=12, gust=22, hum=55, uv=6, pc=10, mm=0.2, sr="04:43", ss="21:21",
                       warn=False, tag="10% rain", sum="Warm with sunny spells."),
            WeatherDay(d="Tue 23", ic="⛅", cond="Cloudy", hi=22, lo=14, feels=22,
                       wind=14, gust=24, hum=60, uv=5, pc=20, mm=0.5, sr="04:43", ss="21:21",
                       warn=False, tag="20% rain", sum="Cloudier with light winds."),
        ],
        sources=[Source(outlet="Met Office", title="Guildford forecast",
                       url="https://www.metoffice.gov.uk/", lean="")],
    )


def build_dry_run_edition() -> "object":
    """Return a fully validated placeholder ``Edition`` (no network/key needed)."""
    meta = _meta()
    stories = [_story_one(), _story_two()]
    existing_archive = [
        {"date": "21 Jun 2026", "edition": "21 June 2026", "cat": "Health",
         "title": "An earlier sample story", "summary": "Placeholder archive entry.",
         "panel": None},
    ]
    return assemble_edition(
        meta=meta,
        weather=_weather(),
        stories=stories,
        markets=_markets(),
        existing_archive=existing_archive,
    )
