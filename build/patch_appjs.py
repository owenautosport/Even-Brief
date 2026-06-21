#!/usr/bin/env python3
"""Bootstrap step 2: lift the three daily-data literals out of app.js.

The reference ``app.js`` hard-codes the day's weather *content* directly in the
script: the 24-hour ``temp`` and ``precip`` arrays and the 7-day ``DAYS`` array.
That is content, not presentation, so it belongs in the data layer.

This converts those literals to read from a ``<script id="wxData">`` JSON island
(rendered per-edition by the template, exactly like ``archiveData``). Every other
byte of the JS - all logic, chart maths, focus mode, theming - is untouched.

Idempotent: running it twice is a no-op (it detects the already-patched form).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "assets" / "app.js"

LOADER = (
    "    var __wx=(function(){try{return JSON.parse("
    "document.getElementById('wxData').textContent)||{};}catch(e){return {};}})();\n"
    "    var temp=(__wx.temp||[]);\n"
    "    var precip=(__wx.precip||[]);"
)


def main() -> None:
    js = APP.read_text(encoding="utf-8")
    if "__wx" in js:
        print("app.js already patched - nothing to do")
        return

    # temp + precip are two consecutive `var temp=[...];` / `var precip=[...];` lines.
    js, n1 = re.subn(
        r"    var temp=\[[^\]]*\];\n    var precip=\[[^\]]*\];",
        LOADER,
        js,
        count=1,
    )
    # DAYS is a multi-line array literal terminated by a line of `    ];`.
    js, n2 = re.subn(
        r"    var DAYS=\[\n.*?\n    \];",
        "    var DAYS=(__wx.days||[]);",
        js,
        count=1,
        flags=re.DOTALL,
    )
    if n1 != 1 or n2 != 1:
        raise SystemExit(f"patch failed: temp/precip={n1} days={n2} (expected 1 each)")

    APP.write_text(js, encoding="utf-8")
    print(f"patched app.js -> reads temp/precip/days from #wxData island")


if __name__ == "__main__":
    main()
