"""Story discovery: find the day's 8-12 significant stories, deduped vs archive.

The output is a list of ``StoryStub`` - a small local model (NOT part of the
edition schema) carrying just enough to drive the per-story research stage.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .schema import Category

if TYPE_CHECKING:  # avoid importing the live client at module load
    from .client import BriefingClient


# --------------------------------------------------------------------------- #
# Local (non-schema) discovery model
# --------------------------------------------------------------------------- #
class StoryStub(BaseModel):
    """A lightweight pointer to a story to be researched and written."""
    id: str                  # url-safe slug, e.g. "iran-talks"
    category: Category
    headline: str            # neutral working headline
    summary: str             # one-line neutral summary
    nav_label: str           # short drawer label


class StubList(BaseModel):
    """Parse target: the discovered slate."""
    stories: list[StoryStub] = Field(min_length=1)


# Editorial guidance shared by discovery (kept neutral / non-emotive). ------- #
_NEUTRALITY = (
    "Write in a flat, even, descriptive newswire register. Do not use emotive, "
    "dramatic, sensational or loaded language and avoid editorialising "
    "adjectives/adverbs (dramatic, shocking, devastating, stunning, landmark, "
    "grim, tragic, bombshell, etc.). State what happened plainly. Any sense of "
    "significance must be attributable to a named source, never asserted in the "
    "briefing's own voice."
)

_SYSTEM = (
    "You are a wire-service news editor for 'Even Brief', a neutral daily global "
    "briefing. " + _NEUTRALITY
)


def _archive_digest(archive_items: list[dict]) -> str:
    """Compact the archive into 'title - summary' lines for dedupe context."""
    lines = []
    for it in archive_items[:120]:
        title = it.get("title", "")
        summ = it.get("summary", "")
        date = it.get("date", "")
        lines.append(f"- [{date}] {title} :: {summ}")
    return "\n".join(lines) if lines else "(archive is empty)"


def discover_stories(
    client: "BriefingClient",
    archive_items: list[dict],
    today_iso: str,
) -> list[StoryStub]:
    """Research and return 8-12 deduped story stubs for ``today_iso``.

    Enforces the 24-hour / one-run-per-story rule: a topic already in the
    archive may only return if there is a genuinely material new development,
    written as a new story.
    """
    digest = _archive_digest(archive_items)
    prompt = (
        f"Today is {today_iso}. Research the most significant news of the last "
        "24 hours across world politics, conflict, science, climate, health, "
        "technology and business/markets. Use web search across independent "
        "outlets (Reuters, AP, BBC, Bloomberg, Guardian, Al Jazeera, NPR, PBS).\n\n"
        "Select 8 to 12 of the most significant stories (international impact, "
        "precedent-setting, unexpected, affecting many people, or major "
        "developments in ongoing situations).\n\n"
        "DEDUPE RULE - the following stories already ran and live in the "
        "archive. Do NOT republish any of them. A topic may return ONLY if there "
        "is a genuinely material NEW development since it last appeared; if so, "
        "frame it as a brand-new story (new angle, new dated facts).\n\n"
        f"ARCHIVE (already published):\n{digest}\n\n"
        "For each chosen story give: a short url-safe slug id; a category (one of "
        "Politics, Conflict, Business, Markets, Health, Science, Technology, "
        "Climate, Sport); a neutral working headline; a one-line neutral summary; "
        "and a short nav label."
    )

    research = client.research(
        prompt=prompt,
        system=_SYSTEM,
        max_searches=10,
    )
    # Structure the gathered research into validated stubs.
    stubs = client.parse(
        output_format=StubList,
        system=_SYSTEM,
        prompt=(
            "From the research notes below, produce the final deduped slate of "
            "8-12 stories as structured data. Keep slugs lowercase and hyphenated "
            "and unique. Keep all text neutral.\n\nRESEARCH NOTES:\n"
            + research.text
        ),
        max_tokens=4000,
    )
    return stubs.stories
