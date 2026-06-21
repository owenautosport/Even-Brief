# Even Brief

> **AI disclosure:** Even Brief is researched, written and fact-checked by an AI system from public, non-paywalled sources. AI can make mistakes — verify anything important independently. Not financial, legal or medical advice.

A self-contained daily news briefing (one HTML file): top stories with fact-checks,
confidence ratings and media-framing analysis, plus markets, live stocks, a full
weather page and a searchable archive.

<!--EDITION:START-->
## Current edition — Sunday, 21 June 2026

Today's Top Headlines:

- **Iran says it has re-closed the Strait of Hormuz; Switzerland talks postponed** — After an Israeli strike on Lebanon, Iran says it has again closed the strait and the US–Iran talks are postponed — the week-old memorandum under strain.
- **Burnham wins Makerfield; a Labour leadership contest opens** — The Manchester mayor took the seat with about 55% and is expected to press Starmer to stand aside.
- **Ukraine strikes Crimea-bridge approaches overnight; trackers still disagree** — Drones hit the Kerch and Kavkaz ports on 21 June; DeepState and ISW give opposite readings of who is gaining ground.
- **The ceasefire's weakest link: Israel and Lebanon** — An Israeli strike on Lebanon on Saturday became the flashpoint that pushed Iran to re-close the strait and stall the talks.
- **Congo Ebola: 896 cases, 232 deaths, a global emergency** — The WHO's highest alert is in force; the Bundibugyo strain still has no licensed vaccine.
- **AI labs step onto the world stage: G7 debut, Seoul office, new benchmark** — Altman, Amodei and Hassabis appeared together at the G7; Anthropic opened a Seoul office and its Fable 5 model topped a hard-maths benchmark.
- **CERN completes the doubly-charmed baryon family** — Physicists report the third and final member, a confirmation of the Standard Model.
- **A California fault is more stressed than in 1,000 years** — Researchers describe an 'earthquake gate' on a system overdue for a major rupture.
- **A hawkish Fed reset the week before the holiday lull** — Markets were shut Friday for Juneteenth; the story remains Warsh's pivot toward a 2026 hike.

Read the live site: https://owenautosport.github.io/Even-Brief/
<!--EDITION:END-->

## How it's published
This folder is the website. `index.html` is the whole site (one self-contained
file), hosted on GitHub Pages (static, free, HTTPS) at
<https://owenautosport.github.io/Even-Brief/>.

`index.html` is **built**, not hand-edited: a generator produces a validated
`content/editions/<date>.json`, and the build renders it through templates +
inlined assets into `index.html` + `archive.json`. See **ARCHITECTURE.md**.

## Updating the site
Two ways to generate an edition (both end at the same build — see **GENERATION.md**):

- **Claude Code mode (no API cost):** in a Claude Code session here, run
  `/new-edition` — it researches the day's news on your subscription, writes the
  edition JSON, and builds. Then `git commit && git push`.
- **API pipeline (metered):** `python -m evenbrief.pipeline` then
  `python -m build.render` — used by the optional nightly GitHub Action once the
  `ANTHROPIC_API_KEY` secret is set (**AUTOMATION.md**).

Build a hand-written/edited edition directly:
```
python -m evenbrief.check_edition content/editions/<date>.json   # validate
python -m build.render --edition content/editions/<date>.json    # build + gate
```

## Develop / test (free, no key)
```
pip install -r requirements.txt -e .
python -m pytest -q                                  # full suite
python -m evenbrief.pipeline --dry-run --out /tmp/e.json && \
  python -m build.render --edition /tmp/e.json --check-only
```

## Notes
- Most of the page works offline; the live stock widgets (TradingView) and the
  rain radar (Leaflet + RainViewer) need an internet connection to load.
- `.nojekyll` tells GitHub Pages to serve files as-is.
- A `LICENSE` (MIT) and the static brand assets (`favicon.svg`, `favicon-32.png`,
  `apple-touch-icon.png`, `og-image.png`) live in the repo root.
