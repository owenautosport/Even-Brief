"""Per-story deep research: gather quotes, stats, timeline, sources.

Produces a ``ResearchDossier`` - a local (non-schema) container that the writer
turns into a schema ``Story`` and the verifier uses for corroboration checks.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .client import BriefingClient
    from .discover import StoryStub


# --------------------------------------------------------------------------- #
# Local (non-schema) dossier models
# --------------------------------------------------------------------------- #
class Quote(BaseModel):
    text: str
    who: str                 # speaker + role
    date: str                # when said


class TimelineFact(BaseModel):
    date: str                # ISO yyyy-mm-dd
    label: str               # display date, e.g. "17 Jun"
    title: str
    detail: str


class SourceNote(BaseModel):
    outlet: str
    title: str
    url: str
    lean: str = ""           # Left / Centre / Right / Wire / Regional
    primary: bool = False    # True if a primary/official source


class ResearchDossier(BaseModel):
    """Everything gathered about one story."""
    stub_id: str
    headline: str
    category: str
    dateline: str = ""               # "22 June 2026 | Geneva"
    background: str = ""
    key_facts: list[str] = Field(default_factory=list)
    quotes: list[Quote] = Field(default_factory=list)
    stats: list[str] = Field(default_factory=list)
    timeline: list[TimelineFact] = Field(default_factory=list)
    sources: list[SourceNote] = Field(default_factory=list)
    agreed_facts: list[str] = Field(default_factory=list)    # all sides agree
    contested_facts: list[str] = Field(default_factory=list)  # in dispute
    whats_next: str = ""


_NEUTRALITY = (
    "Neutral newswire register. No emotive/loaded/editorialising language. State "
    "facts and clearly-attributed claims only. Record WHO said each quote and the "
    "DATE. Note each outlet's rough political lean for the bias bar. Prefer and "
    "link primary sources."
)

_SYSTEM = (
    "You are a wire-service researcher for 'Even Brief'. " + _NEUTRALITY
)


def research_story(client: "BriefingClient", stub: "StoryStub") -> ResearchDossier:
    """Run 5+ targeted searches across independent outlets and build a dossier."""
    prompt = (
        f"Deep-research this story for a neutral daily briefing.\n\n"
        f"WORKING HEADLINE: {stub.headline}\n"
        f"CATEGORY: {stub.category}\n"
        f"SUMMARY: {stub.summary}\n\n"
        "Run at least 5 targeted web searches across independent outlets "
        "(Reuters, AP, BBC, Bloomberg, Guardian, CNN, Al Jazeera, NPR, PBS). "
        "Fetch primary/official sources where possible. Gather:\n"
        "- background and what comes next;\n"
        "- key facts (numbers, dates, names);\n"
        "- direct quotes, each with WHO said it and the DATE;\n"
        "- a dated timeline of events (ISO dates);\n"
        "- which outlets cover it and roughly where each sits politically "
        "(Left/Centre/Right/Wire/Regional);\n"
        "- facts ALL sides agree on vs facts that are contested;\n"
        "- working source links, flagging which are primary/official."
    )
    research = client.research(
        prompt=prompt,
        system=_SYSTEM,
        max_searches=8,
    )

    dossier = client.parse(
        output_format=ResearchDossier,
        system=_SYSTEM,
        prompt=(
            "Structure the research notes below into a dossier. Keep all prose "
            "neutral and factual. Use ISO dates (yyyy-mm-dd) in the timeline. "
            f"Set stub_id to '{stub.id}', headline to a neutral final headline, "
            f"and category to '{stub.category}'.\n\nRESEARCH NOTES:\n"
            + research.text
        ),
        max_tokens=8000,
    )
    # Fold any sources the loop collected but the model didn't enumerate.
    have = {s.url for s in dossier.sources}
    for s in research.sources:
        if s["url"] not in have:
            dossier.sources.append(
                SourceNote(outlet="", title=s.get("title", ""), url=s["url"])
            )
            have.add(s["url"])
    return dossier
