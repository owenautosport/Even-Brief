"""Verification pass (Opus): fact-check tags, confidence, logic flags.

This runs after writing. It NEVER drops a story; it flags issues instead. It:
* adds a FactCheck block (✅ confirmed / 🔍 unverified) naming corroboration;
* sets the overall Confidence level (Verified / Developing / Disputed);
* adds a LogicFlags block when internal-consistency issues exist;
* downgrades single-source major claims to 🔍 Unverified and lowers confidence.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .schema import (
    Confidence,
    ConfidenceLevel,
    FactCheck,
    FactCheckItem,
    LogicFlags,
    Story,
)

if TYPE_CHECKING:
    from .client import BriefingClient
    from .research import ResearchDossier

_LABEL = {"corrob": "Verified", "develop": "Developing", "disputed": "Disputed"}


class _FCItem(BaseModel):
    status: str              # "ok" | "unv"
    verdict: str             # "Confirmed" | "Unverified"
    text: str


class _Verdict(BaseModel):
    """Parse target for the Opus verification pass."""
    confidence_level: ConfidenceLevel
    confidence_why: str
    factchecks: list[_FCItem] = Field(min_length=1)
    logic_flags: list[str] = Field(default_factory=list)


def _article_text(story: Story) -> str:
    parts: list[str] = [story.headline, story.summary]
    for b in story.article_blocks:
        if getattr(b, "type", None) == "p":
            parts.append(b.html)  # type: ignore[attr-defined]
    return "\n".join(parts)


def verify_story(
    client: "BriefingClient",
    story: Story,
    dossier: "ResearchDossier",
) -> Story:
    """Run the Opus verification pass and return the annotated ``Story``."""
    source_lines = "\n".join(
        f"- {s.outlet or s.url}: {s.title} [{s.lean or 'lean unknown'}] {s.url}"
        for s in dossier.sources
    ) or "(no sources recorded)"

    verdict = client.parse(
        output_format=_Verdict,
        model="claude-opus-4-8",
        opus_effort=True,
        system=(
            "You are a meticulous wire-service fact-checker and logic auditor for "
            "'Even Brief'. Be neutral and non-emotive. Corroborate major claims "
            "across 2+ independent sources. Mark any major claim resting on a "
            "single source as Unverified (status 'unv') and lower confidence "
            "accordingly. Never recommend dropping a story; flag transparently."
        ),
        prompt=(
            "Assess this article against the gathered sources.\n\n"
            "Return:\n"
            "1. confidence_level: 'corrob' (Verified - well corroborated), "
            "'develop' (Developing - fast-moving/partial), or 'disputed' "
            "(Disputed - sources conflict).\n"
            "2. confidence_why: a short trailing clause explaining the level.\n"
            "3. factchecks: one item per major claim with status 'ok' "
            "(Confirmed, 2+ sources) or 'unv' (Unverified/single-source), a "
            "verdict word, and the claim text naming corroborating sources.\n"
            "4. logic_flags: numbered internal-consistency checks - interrogate "
            "numbers, timelines, cause-vs-effect, correlation-vs-causation. "
            "Include checks even when they pass; leave empty only if nothing to "
            "note.\n\n"
            f"ARTICLE:\n{_article_text(story)}\n\n"
            f"SOURCES:\n{source_lines}\n"
        ),
        max_tokens=6000,
    )

    # Apply confidence.
    story.confidence = Confidence(
        level=verdict.confidence_level,
        label=_LABEL[verdict.confidence_level],
        why=verdict.confidence_why,
    )

    # Build/insert the FactCheck sidebar block.
    fc_items = [
        FactCheckItem(
            status="ok" if it.status == "ok" else "unv",
            verdict=it.verdict or ("Confirmed" if it.status == "ok" else "Unverified"),
            text=it.text,
        )
        for it in verdict.factchecks
    ]
    story.sidebar_blocks.append(FactCheck(items=fc_items))

    # Add LogicFlags only when there is something to show.
    if verdict.logic_flags:
        story.sidebar_blocks.append(LogicFlags(items=verdict.logic_flags))

    return story
