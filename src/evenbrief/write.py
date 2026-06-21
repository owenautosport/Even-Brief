"""Story writing: turn a ResearchDossier into a validated schema ``Story``.

The writer produces neutral newswire prose as ordered ``article_blocks``
(Paragraph / PullQuote / Timeline / Framing) and ``sidebar_blocks`` (KeyFacts /
Sources / FactCheck / CommonGround / LogicFlags). The verifier (verify.py) then
sets fact-check tags, confidence and logic flags. We keep the heavy structural
fields (timeline, sources, framing) deterministic here, and let the model write
the prose, so the output reliably validates.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .schema import (
    Badge,
    BiasSegment,
    CommonGround,
    Confidence,
    Framing,
    KeyFacts,
    Paragraph,
    PullQuote,
    Sources,
    Source,
    Story,
    Timeline,
    TimelineEvent,
)

if TYPE_CHECKING:
    from .client import BriefingClient
    from .research import ResearchDossier


# Category -> badge CSS modifier + placeholder tile class + emoji. ----------- #
_CATEGORY_STYLE = {
    "Politics":   ("b-politics", "cat-politics", "\U0001F3DB"),   # classical building
    "Conflict":   ("b-conflict", "cat-conflict", "⚠"),       # warning
    "Business":   ("b-business", "cat-business", "\U0001F4BC"),   # briefcase
    "Markets":    ("b-markets", "cat-markets", "\U0001F4C8"),     # chart up
    "Health":     ("b-health", "cat-health", "\U0001FA7A"),       # stethoscope
    "Science":    ("b-science", "cat-science", "\U0001F52C"),     # microscope
    "Technology": ("b-technology", "cat-technology", "\U0001F4BB"),  # laptop
    "Climate":    ("b-climate", "cat-climate", "\U0001F30D"),     # globe
    "Sport":      ("b-sport", "cat-sport", "⚽"),             # football
}

_LEAN_COLOR = {
    "Left": "#3b82c4",
    "Centre": "#9aa0ac",
    "Center": "#9aa0ac",
    "Right": "#c4513b",
    "Wire": "#cda349",
    "Regional": "#48c78e",
}

_NEUTRALITY = (
    "NEUTRALITY RULE: write in a flat, even, descriptive newswire register. No "
    "emotive, dramatic, sensational or loaded language; avoid editorialising "
    "adjectives/adverbs. State what happened and the numbers plainly. Do not "
    "cheerlead, alarm, or imply approval. Any characterisation must be attributed "
    "to a named source, never asserted in the briefing's own voice. If an "
    "adjective can be deleted without losing information, delete it."
)


class _Prose(BaseModel):
    """What the model writes; structural blocks are assembled in Python."""
    headline: str
    summary: str
    dateline: str                        # "22 June 2026 | Geneva"
    paragraphs: list[str] = Field(min_length=1)   # 7-10 neutral paragraphs (HTML ok)
    pull_quote_text: str = ""
    pull_quote_src: str = ""
    bias_overview: str = ""              # for the framing box
    framing_lines: list[str] = Field(default_factory=list)


def _badges(category: str) -> list[Badge]:
    cls, _, _ = _CATEGORY_STYLE.get(category, ("b-politics", "cat-politics", "\U0001F4F0"))
    return [Badge(label=category, cls=cls)]


def _build_timeline(dossier: "ResearchDossier") -> list[TimelineEvent]:
    out: list[TimelineEvent] = []
    for t in dossier.timeline:
        out.append(
            TimelineEvent(date=t.date, label=t.label, title=t.title, detail=t.detail)
        )
    return out


def _build_sources(dossier: "ResearchDossier") -> list[Source]:
    out: list[Source] = []
    for s in dossier.sources:
        if not s.url:
            continue
        out.append(
            Source(
                outlet=s.outlet or s.url.split("/")[2] if "//" in s.url else (s.outlet or "source"),
                title=s.title or s.outlet or "source",
                url=s.url,
                lean=s.lean,
            )
        )
    return out


def _build_framing(dossier: "ResearchDossier", overview: str, lines: list[str]):
    """Build the bias bar from the leans recorded across gathered sources."""
    counts: dict[str, int] = {}
    for s in dossier.sources:
        lean = (s.lean or "").strip().title()
        if lean in ("Center",):
            lean = "Centre"
        if lean in ("Left", "Centre", "Right"):
            counts[lean] = counts.get(lean, 0) + 1
    total = sum(counts.values())
    segments: list[BiasSegment] = []
    if total:
        for lean in ("Left", "Centre", "Right"):
            if counts.get(lean):
                pct = round(counts[lean] / total * 100)
                segments.append(
                    BiasSegment(lean=lean, pct=pct, color=_LEAN_COLOR[lean])
                )
    if not segments:
        # Neutral default when leans weren't recorded.
        segments = [BiasSegment(lean="Centre", pct=100, color=_LEAN_COLOR["Centre"])]
    return Framing(
        overview=overview or "<strong>Political-bias overview:</strong> coverage drawn from a mix of outlets.",
        bias=segments,
        lines=lines,
    )


def write_story(client: "BriefingClient", dossier: "ResearchDossier") -> Story:
    """Produce a schema ``Story`` from a dossier (prose via model, structure in code)."""
    quotes_block = "\n".join(
        f'- "{q.text}" -- {q.who}, {q.date}' for q in dossier.quotes
    ) or "(none recorded)"
    stats_block = "\n".join(f"- {s}" for s in dossier.stats) or "(none)"

    prose = client.parse(
        output_format=_Prose,
        system="You are a wire-service writer for 'Even Brief'. " + _NEUTRALITY,
        prompt=(
            "Write a neutral, in-depth article (7-10 paragraphs) from this "
            "dossier. Use only facts and clearly-attributed claims present here. "
            "Inline HTML tags <strong>/<em> are permitted but keep them sparse. "
            "Provide: final neutral headline; one-line summary; a dateline like "
            "'22 June 2026 | Location'; the paragraphs; optionally one pull quote "
            "(text + dated attribution like '-- Role, 22 June 2026'); a short "
            "bias overview sentence; and 1-3 framing lines describing how "
            "different outlets are covering it.\n\n"
            f"HEADLINE: {dossier.headline}\nCATEGORY: {dossier.category}\n"
            f"BACKGROUND: {dossier.background}\n"
            f"KEY FACTS:\n" + "\n".join(f"- {k}" for k in dossier.key_facts) + "\n"
            f"STATS:\n{stats_block}\n"
            f"QUOTES:\n{quotes_block}\n"
            f"WHAT'S NEXT: {dossier.whats_next}\n"
        ),
        max_tokens=8000,
    )

    cls, _, _ = _CATEGORY_STYLE.get(
        dossier.category, ("b-politics", "cat-politics", "\U0001F4F0")
    )

    # ----- assemble ordered article blocks -------------------------------- #
    article_blocks: list = []
    paras = [Paragraph(html=p) for p in prose.paragraphs]
    # Drop a pull quote after the second paragraph if we have one.
    if prose.pull_quote_text:
        pq = PullQuote(text=prose.pull_quote_text, src=prose.pull_quote_src)
        insert_at = min(2, len(paras))
        article_blocks = paras[:insert_at] + [pq] + paras[insert_at:]
    else:
        article_blocks = list(paras)

    timeline_events = _build_timeline(dossier)
    if len(timeline_events) >= 2:
        article_blocks.append(
            Timeline(events=timeline_events, note=dossier.whats_next or "")
        )

    framing = _build_framing(dossier, prose.bias_overview, prose.framing_lines)
    article_blocks.append(framing)

    # ----- assemble sidebar blocks ---------------------------------------- #
    sidebar_blocks: list = []
    key_facts = dossier.key_facts or ([dossier.summary] if dossier.background else [])
    if key_facts:
        sidebar_blocks.append(KeyFacts(items=key_facts))

    sources = _build_sources(dossier)
    if sources:
        sidebar_blocks.append(Sources(items=sources))

    if dossier.agreed_facts or dossier.contested_facts:
        sidebar_blocks.append(
            CommonGround(agree=dossier.agreed_facts, contest=dossier.contested_facts)
        )

    # FactCheck / LogicFlags / Confidence are finalised by verify.py.
    return Story(
        id=dossier.stub_id,
        nav_label=prose.headline[:60],
        category=dossier.category,  # type: ignore[arg-type]
        badges=_badges(dossier.category),
        dateline=prose.dateline or dossier.dateline,
        headline=prose.headline,
        summary=prose.summary,
        confidence=Confidence(level="develop", label="Developing", why="pending verification"),
        article_blocks=article_blocks,
        sidebar_blocks=sidebar_blocks,
    )
