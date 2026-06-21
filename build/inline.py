"""Asset inlining for the self-contained build.

The source keeps CSS and JS as separate, maintainable files under ``assets/``.
At render time their contents are folded back into the single ``index.html`` so
the published artifact stays one self-contained file - byte-faithful to the
original reference design.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"


def load_assets() -> dict[str, str]:
    """Return the verbatim stylesheet and app script to inline into the page."""
    return {
        "styles_css": (ASSETS / "styles.css").read_text(encoding="utf-8").rstrip("\n"),
        "app_js": (ASSETS / "app.js").read_text(encoding="utf-8").rstrip("\n"),
    }
