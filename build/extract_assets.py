#!/usr/bin/env python3
"""One-off bootstrap: split the reference index.html into verbatim CSS/JS assets.

This is run ONCE to deconstruct the original hand-built ``index.html`` into the
maintainable source the build pipeline reuses:

* ``reference/index.html``  - frozen golden copy (design-parity fixture)
* ``assets/styles.css``     - the entire <style> block, byte-for-byte
* ``assets/app.js``         - the main application <script>, byte-for-byte

The extracted assets are reassembled verbatim into the rendered output by
``build/inline.py`` so the published page stays a single self-contained file.

After this runs, three daily-data literals inside ``app.js`` (the hourly temp /
precip arrays and the 7-day DAYS array) are converted to read from a JSON data
island by ``build/patch_appjs.py`` - the JS *logic* stays identical, only the
embedded content is lifted out into the data layer.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"


def _between(text: str, open_marker: str, close_marker: str, start: int = 0):
    """Return (inner, open_idx, close_end) for the first marker pair after start."""
    o = text.index(open_marker, start)
    body_start = o + len(open_marker)
    c = text.index(close_marker, body_start)
    return text[body_start:c], o, c + len(close_marker)


def main() -> None:
    html = SRC.read_text(encoding="utf-8")

    # 1. Freeze the golden reference.
    ref = ROOT / "reference" / "index.html"
    shutil.copyfile(SRC, ref)
    print(f"froze {ref.relative_to(ROOT)}")

    # 2. Extract the <style> block (there is exactly one).
    css, _, _ = _between(html, "<style>", "</style>")
    css = css.strip("\n") + "\n"
    (ROOT / "assets" / "styles.css").write_text(css, encoding="utf-8")
    print(f"wrote assets/styles.css ({len(css)} bytes)")

    # 3. Extract the main application <script> - the last <script> with no src,
    #    which opens immediately after the Leaflet CDN <script src=...> tag.
    leaflet = html.index("leaflet.min.js")
    app_open = html.index("<script>", leaflet)
    inner, _, _ = _between(html, "<script>", "</script>", app_open)
    inner = inner.strip("\n") + "\n"
    (ROOT / "assets" / "app.js").write_text(inner, encoding="utf-8")
    print(f"wrote assets/app.js ({len(inner)} bytes)")


if __name__ == "__main__":
    main()
