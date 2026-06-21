# Even Brief — Architecture

Even Brief is a daily AI-compiled news briefing published as a single
self-contained `index.html` on GitHub Pages. The repo is split into a
**generation backend** (researches the day's news) and a **build step**
(renders it into the site), meeting at one validated data contract.

```
            ANTHROPIC API (web_search / web_fetch)
                          │
        ┌─────────────────▼──────────────────┐
        │  GENERATION  (src/evenbrief/)       │
        │  discover → research → write →      │
        │  verify  ┐                          │
        │  markets ├─► assemble ─► Edition ───┼──► content/editions/<date>.json
        │  weather ┘   (validated)            │
        └─────────────────┬──────────────────┘
                          │  edition.json (DATA, not HTML)
        ┌─────────────────▼──────────────────┐
        │  BUILD  (build/)                    │
        │  render ─► Jinja(templates/) +      │
        │            inline(assets/) ─► HTML  │
        │  validate (gate) ──────────────────┼──► index.html
        └─────────────────┬──────────────────┘     archive.json
                          │                          template-reference.html
                          │                          sitemap.xml · README block
                   GitHub Pages (static, free)
```

## 1. Content layer — the contract (`src/evenbrief/schema.py`)

Pydantic v2 models define what an **`Edition`** is: `meta`, `weather`,
`headlines`, `stories`, `markets`, `archive`. The key design choice is that an
article is an **ordered list of blocks** — `article_blocks`
(`Paragraph` / `PullQuote` / `Timeline` / `Framing`) and `sidebar_blocks`
(`KeyFacts` / `Sources` / `FactCheck` / `CommonGround` / `LogicFlags` /
`Framing`). This mirrors the reference, where a timeline, pull-quote or
media-framing box can appear at any point, and the framing box lives in the
article on some stories and in the sidebar rail on others.

Editions are JSON in `content/editions/<date>.json`; the growing archive is
`archive.json` at the repo root. JSON Schemas are emitted to
`content/schema/`.

## 2. Presentation layer (`templates/`, `assets/`)

The original hand-built page was deconstructed **once** (`build/extract_assets.py`)
into:

* `assets/styles.css` — the entire `<style>` block, **byte-for-byte**;
* `assets/app.js` — the application script, byte-for-byte except that three
  daily-data literals (the 24-hour temp/precip arrays and the 7-day `DAYS`
  array) were lifted into a `<script id="wxData">` JSON island
  (`build/patch_appjs.py`) — so the JS holds *logic*, the edition holds *content*;
* `templates/base.html.j2` + `templates/partials/` — the page skeleton and
  component macros (`story_panel`, `headline_card`, `movers_panel`,
  `calendar_panel`, `weather_panel`, …) that reproduce the reference markup
  exactly and fill only the data.

The frozen original lives at `reference/index.html` and is the design-parity
fixture the tests compare against.

> **Single-file output vs DRY source.** Source is maintainable (separate CSS/JS
> + partials); the build **inlines** the assets back so the published artifact
> stays one self-contained file, faithful to the reference.

## 3. Generation backend (`src/evenbrief/`)

Modular `research → write → verify → assemble`, each piece independently
testable and re-runnable:

| Module | Responsibility |
|---|---|
| `client.py` | `BriefingClient` over the Anthropic SDK (server-side `web_search_20260209` / `web_fetch_20260209`); structured `parse()` with retries; `research()` tool loop; `CostMeter` |
| `discover.py` | find 8–12 significant stories; dedupe vs `archive.json` (24-hour rule) |
| `research.py` | 5+ searches/story; quotes (who + date), stats, dated timeline, sources + lean |
| `write.py` | neutral-newswire `Story` (ordered blocks; bias bar from source leans) |
| `verify.py` | Opus fact-check ✅/🔍, confidence (Verified/Developing/Disputed), logic flags; flags single-source items rather than dropping them |
| `markets.py` | overview (a `Story`) + movers + month calendar; 2+ sources; no invented tickers |
| `weather.py` | Guildford masthead/current/warnings + 24h arrays + 7-day + Met Office sources |
| `images.py` | licence-safe images only (Wikimedia Commons / NASA / USGS / CDC …); else `None` |
| `assemble.py` | build headlines, merge archive (dedupe), construct & validate `Edition` |
| `pipeline.py` | orchestrator; `--dry-run` builds a valid edition offline (no key/network) |

Models: `claude-sonnet-4-6` for high-volume research/writing, `claude-opus-4-8`
(adaptive thinking, high effort) for verification/logic.

## 4. Build & validation (`build/`)

`build/render.py` loads an edition, renders `base.html.j2` with the inlined
assets, and writes `index.html`, `archive.json`, `template-reference.html`,
refreshes `sitemap.xml` and the README `<!--EDITION:START/END-->` block.

`build/validate.py` is the **gate** — the build fails (no commit) if the HTML
doesn't parse, a required component/selector is missing, the canonical palette
drifted, the archive JSON is broken/duplicated, a story lacks sources, an image
isn't on the open-licence allowlist, or a story repeats an older archive
headline (24-hour/dedupe rule).

## 5. Tests (`tests/`)

Pytest, all offline (driven by the dry-run edition): schema validity, render +
design-parity, asset byte-fidelity vs the reference, data-island validity,
SEO/JSON-LD presence, and that the gate *rejects* malformed editions (dupes,
sourceless stories, non-open images, reposted headlines).

## 6. Two generation front-ends

Both produce the same validated `Edition` → the same build, so editions look and
behave identically however they were made (see **GENERATION.md**):

* **Claude Code mode** — Claude Code researches the news on your *subscription*
  (its own WebSearch/WebFetch) and writes the edition JSON. No API key, no API
  spend. Run `/new-edition` in a Claude Code session here. The edition only needs
  *today's* archive items; `build/render.py` merges the prior `archive.json`.
* **API pipeline** (`src/evenbrief/`) — the metered Anthropic-API path above,
  for unattended runs.

## 7. Automation

See **AUTOMATION.md**. `.github/workflows/daily.yml` runs the API pipeline
generate → build → commit ~06:30 London (needs the `ANTHROPIC_API_KEY` secret);
`.github/workflows/ci.yml` runs the test suite on every push/PR (no key).
