"""Assemble a validated ``Edition`` from stories, markets, weather and archive.

Responsibilities:
* build the Headlines hero + cards from the day's stories;
* merge today's stories into the archive (newest first, dedup by title);
* construct and validate ``Edition(**...)``.
"""
from __future__ import annotations

from .schema import (
    ArchiveItem,
    Edition,
    HeadlineCard,
    Headlines,
    Markets,
    Meta,
    Story,
    Weather,
)

# Category -> (placeholder tile class, emoji) for headline cards. ------------ #
_CAT_TILE = {
    "Politics":   ("cat-politics", "\U0001F3DB"),
    "Conflict":   ("cat-conflict", "⚠"),
    "Business":   ("cat-business", "\U0001F4BC"),
    "Markets":    ("cat-markets", "\U0001F4C8"),
    "Health":     ("cat-health", "\U0001FA7A"),
    "Science":    ("cat-science", "\U0001F52C"),
    "Technology": ("cat-technology", "\U0001F4BB"),
    "Climate":    ("cat-climate", "\U0001F30D"),
    "Sport":      ("cat-sport", "⚽"),
}


def _card(story: Story, lead: bool) -> HeadlineCard:
    tile_cls, emoji = _CAT_TILE.get(story.category, ("cat-politics", "\U0001F4F0"))
    return HeadlineCard(
        target=story.id,
        badge=story.badges[0],
        cat_cls=tile_cls,
        emoji=emoji,
        headline=story.headline,
        summary=story.summary,
        image_url=story.image.url if story.image else None,
        lead=lead,
    )


def build_headlines(stories: list[Story]) -> Headlines:
    """Hero from the first story; cards from the rest (plus the hero as a card)."""
    if not stories:
        raise ValueError("cannot build headlines from an empty story list")
    hero = _card(stories[0], lead=True)
    cards = [_card(s, lead=(i == 0)) for i, s in enumerate(stories)]
    return Headlines(hero=hero, cards=cards)


def _story_to_archive(story: Story, meta: Meta) -> ArchiveItem:
    # date like "22 Jun 2026" from edition label "22 June 2026".
    parts = meta.edition_label.split()
    short_date = meta.edition_label
    if len(parts) == 3:
        short_date = f"{parts[0]} {parts[1][:3]} {parts[2]}"
    return ArchiveItem(
        date=short_date,
        edition=meta.edition_label,
        cat=story.category,
        title=story.headline,
        summary=story.summary,
        panel=story.id,
    )


def merge_archive(
    new_items: list[ArchiveItem],
    existing: list[dict],
) -> list[ArchiveItem]:
    """New items first, then existing; dedup by (case-insensitive) title.

    Existing items keep their stored ``panel`` cleared unless they belong to a
    prior edition - panels only point into the *current* edition, so we strip
    panels from carried-over items.
    """
    out: list[ArchiveItem] = []
    seen: set[str] = set()
    for it in new_items:
        key = it.title.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    for raw in existing:
        title = (raw.get("title") or "").strip()
        key = title.lower()
        if not title or key in seen:
            continue
        seen.add(key)
        # Carried-over items are not part of today's edition: drop the panel link.
        item = ArchiveItem(
            date=raw.get("date", ""),
            edition=raw.get("edition", ""),
            cat=raw.get("cat", "Politics"),
            title=title,
            summary=raw.get("summary", ""),
            panel=None,
        )
        out.append(item)
    return out


def assemble_edition(
    *,
    meta: Meta,
    weather: Weather,
    stories: list[Story],
    markets: Markets,
    existing_archive: list[dict],
) -> Edition:
    """Combine the parts and return a validated ``Edition``."""
    headlines = build_headlines(stories)
    new_archive = [_story_to_archive(s, meta) for s in stories]
    archive = merge_archive(new_archive, existing_archive)

    # Construct + validate. Passing through model_validate re-checks everything.
    edition = Edition(
        meta=meta,
        weather=weather,
        headlines=headlines,
        stories=stories,
        markets=markets,
        archive=archive,
    )
    return edition
