"""Licence-safe image lookup.

Returns an ``Image`` ONLY when its URL is on the public-domain / open-licence
host allowlist. Anything else returns ``None`` rather than guessing - the build
gate (validate.py) enforces the same allowlist, so a bad guess would fail the run.

Allowed hosts:
* commons.wikimedia.org  (Special:FilePath/<file>)
* upload.wikimedia.org
* openverse / *.openverse.* / openverse.org
* *.nasa.gov
* usgs.gov / *.usgs.gov
* cdc.gov / *.cdc.gov / phil.cdc.gov
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import quote, urlparse

from .schema import Image

# Suffix-matched allowlist (host must equal or end with one of these). ------- #
_ALLOWED_SUFFIXES = (
    "commons.wikimedia.org",
    "upload.wikimedia.org",
    "openverse.org",
    "openverse.engineering",
    ".nasa.gov",
    "nasa.gov",
    "usgs.gov",
    "cdc.gov",
    "phil.cdc.gov",
)


def is_allowed_host(url: str) -> bool:
    """True if ``url``'s host is on the licence-safe allowlist."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    for suf in _ALLOWED_SUFFIXES:
        if suf.startswith("."):
            if host.endswith(suf):
                return True
        elif host == suf or host.endswith("." + suf):
            return True
    return False


def commons_filepath_url(filename: str, width: Optional[int] = None) -> str:
    """Build a Wikimedia Commons Special:FilePath URL for a known filename.

    Special:FilePath resolves to the actual media file and is stable. The caller
    is responsible for using a *verified* filename - we never invent one.
    """
    name = filename.strip().replace(" ", "_")
    if name.lower().startswith("file:"):
        name = name.split(":", 1)[1]
    url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(name)
    if width:
        url += f"?width={int(width)}"
    return url


def find_image(client_or_query) -> Optional[Image]:
    """Return a licence-safe ``Image`` or ``None``.

    Accepts either:
    * a dict/``Image``-like mapping describing a candidate (url, alt, caption,
      credit, license) - validated against the allowlist; or
    * a plain string treated as a verified Commons filename; or
    * anything else -> ``None`` (we do not guess).

    A live image-search via the API can be wired in later, but it must funnel
    every candidate URL through ``is_allowed_host`` before returning it.
    """
    cand = client_or_query

    # Case 1: a mapping describing a specific candidate image.
    if isinstance(cand, dict):
        url = cand.get("url", "")
        if url and is_allowed_host(url):
            return Image(
                url=url,
                alt=cand.get("alt", "") or "News illustration",
                caption=cand.get("caption", ""),
                credit=cand.get("credit", ""),
                license=cand.get("license", ""),
            )
        return None

    # Case 2: a bare verified Commons filename string.
    if isinstance(cand, str) and cand.strip():
        # Heuristic: looks like a filename (has an image extension), not a query.
        lowered = cand.lower()
        if lowered.endswith((".jpg", ".jpeg", ".png", ".svg", ".webp", ".tif", ".tiff", ".gif")):
            url = commons_filepath_url(cand)
            return Image(
                url=url,
                alt="News illustration",
                caption="Photo: Wikimedia Commons",
                credit="Wikimedia Commons",
                license="see file page",
            )
        return None

    # Case 3: unknown input - never guess.
    return None
