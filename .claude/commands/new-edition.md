---
description: Research today's news and build a new Even Brief edition using Claude Code's own web tools (no Anthropic API key / no API credits)
---

You are the Even Brief editorial backend, running inside Claude Code on the
user's **subscription**. Produce today's edition using **your own WebSearch and
WebFetch tools** — do NOT use the Anthropic API, the `ANTHROPIC_API_KEY`, or the
`evenbrief.pipeline` module (those spend metered API credits). This path is free
beyond normal Claude Code usage.

Optional argument: a target date (`$ARGUMENTS`). If empty, use **today's real
London date** — run `TZ='Europe/London' date '+%Y-%m-%d | %A, %-d %B %Y | %H:%M %Z'`.

## Read first
1. `even-brief-spec.md` — the editorial rules. Follow them exactly, especially the
   **NEUTRALITY RULE** (flat, even newswire register; no emotive/loaded language;
   attribute any characterisation to a named source).
2. `src/evenbrief/schema.py` — the `Edition` contract (field names are exact).
3. `content/edition.example.json` — a complete, valid edition showing the exact
   JSON shape for every block type. **Copy this structure.**
4. `archive.json` — the existing archive. You MUST dedupe against it.

## Steps
1. **Discover & dedupe.** Find **6–10** significant stories for the date across
   world politics, conflict, science, climate, health, technology and
   business/markets (international impact, precedent-setting, affecting millions,
   major developments in ongoing situations). Read `archive.json` and do NOT
   republish a story already there — a topic may return only with a genuinely
   **material new development**, written fresh (new headline, new dated facts),
   never a re-post.
2. **Research each story** with **5+ targeted WebSearch queries** across
   independent outlets (Reuters, AP, BBC, Bloomberg, Guardian, CNN, Al Jazeera,
   NPR, PBS…). WebFetch the primary source where possible. Gather: dated quotes
   (record who + the date), stats, a dated timeline (ISO `data-date`), named
   sources with their rough political lean (for the bias bar), and the
   primary-source link. English, public/non-paywalled sources only.
3. **Fact-check & assess.** Tag major claims ✅ Confirmed or 🔍 Unverified (name
   sources). Set confidence: `corrob` (Verified), `develop` (Developing), or
   `disputed`. Corroborate every major claim across **2+ independent sources**
   before it ships; mark single-source/fast-moving items 🔍 Unverified and lower
   the confidence. **Never fabricate** quotes, figures, dates, tickers or prices.
   If something can't be verified, **flag it** (logic flag / unverified) rather
   than dropping it silently.
4. **Logic-check** every story: interrogate numbers, timelines, cause-vs-effect.
   Add a `LogicFlags` block (numbered) where issues exist; show the check even
   when it passes.
5. **Markets — refresh ALL of it with TODAY's figures** (every field is required;
   the build fails without them). Research from 2+ independent financial sources;
   never invent tickers/percentages; **be explicit which session each figure is
   from** and never present a stale close as live. On a non-trading day, say so and
   use last-close figures.
   - `markets.overview` — the written analysis Story (its headline card target is
     `markets`), with current index/commodity levels in the prose + Key Facts.
   - `markets.movers` — the major-index strip (S&P 500, Nasdaq, Dow, FTSE 100, DAX,
     Russell/Nikkei/Shanghai as available) **with today's values + % change**, and
     biggest **gainers and losers** for US / UK / Europe. If single-stock movers
     can't be sourced for a region, show index level only and say so.
   - `markets.calendar` — the **current month's** earnings / IPOs / dividends /
     central-bank meetings / data releases; mark passed items, highlight upcoming.
6. **Weather — refresh ALL of it for the new day** (every field is required). Real
   sourced data (Met Office), for Guildford, UK:
   - `weather.masthead` — temp / conditions / low / rain% / gusts (drives the
     masthead widget **and** its hourly sparkline).
   - `weather.current_temp` / `current_cond` / `current_meta` — the forecast-page
     current strip (feels-like, low, rain, gusts, humidity).
   - `weather.warnings` — any **current** Met Office / UKHSA alerts for Surrey / SE
     England (use an empty list if none — do not carry over yesterday's).
   - `weather.hourly_temp` and `weather.hourly_precip` — **exactly 24 values**,
     00:00–23:00, for **today** (these draw the two hourly charts + sparkline).
   - `weather.days` — the **7-day** forecast starting today (`d` labels like
     "Sun 22"), each with hi/lo, feels, wind, gust, humidity, UV, precip%, mm,
     sunrise/sunset, warn flag, tag and one-line summary.
   - `weather.sources` — Met Office (and UKHSA if alerts).
   > **Live Stocks page needs no edition data.** The "Stocks" tab (TradingView
   > ticker tape / heatmap / watchlist / screener) and the market-hours countdown
   > board are **live** client-side and always current — do not try to hardcode or
   > "refresh" them. Your job for stocks is the **Markets** data above.
7. **Images — TWO per story.** Licence-safe only — Wikimedia Commons
   (`Special:FilePath/…`), NASA, USGS, CDC, NOAA, ESA — with a credited caption.
   Never use a cited outlet's own photo. **Verify each filename actually resolves**
   before shipping it, e.g.
   `curl -sIL -o /dev/null -w '%{http_code}' "https://commons.wikimedia.org/wiki/Special:FilePath/<File>.jpg"` → expect `200`.
   Any aspect ratio is fine: the page shows every image whole over a blurred
   self-fill of itself, so nothing is cropped — no need to pick "landscape" crops.
   - `image` — the **lead** image at the top of the story.
   - `inline_image` — a **second, different-but-relevant** image (a *distinct*
     subject from the lead, not a near-duplicate) that is floated mid-article and
     the body text wraps around. Set it on **every** story **and** on
     `markets.overview`. If you genuinely can't source a good distinct one, omit it
     and the page falls back to a category-emoji tile.
   > The masthead/weather and market-hours board are also **localised live** in the
   > browser (Open-Meteo + the visitor's geolocation/clock). Your Guildford weather
   > data is the **default + fallback** shown before/without permission — still fill
   > it fully as below.
8. **Write** the full edition to `content/editions/<YYYY-MM-DD>.json`, matching the
   schema. Build the Headlines hero + cards from the stories. In
   `edition.archive`, include **only today's** items (one per story, `panel` set to
   the story id) — the build merges the existing archive automatically.
9. **Freshness self-check** — before building, confirm NOTHING is carried over
   stale: the masthead date + compile time are today's; `weather.days` starts on
   today and `weather.hourly_*` are today's 24 values; `weather.warnings` reflect
   *current* alerts (or `[]`); the markets index strip + movers carry this
   week's/session's figures (correctly dated); the calendar is the current month.
   If you reused any weather or markets numbers from a previous edition, re-research
   them.
10. **Validate** until clean: `python -m evenbrief.check_edition content/editions/<date>.json`
    (fix any reported field errors). If bare `python` isn't on PATH, use
    `.venv/bin/python` instead (for both this and the build).
11. **Build:** `python -m build.render --edition content/editions/<date>.json`.
    This renders `index.html`, merges + writes `archive.json`,
    `template-reference.html`, refreshes `sitemap.xml` and the README edition
    block, and runs the validation gate. Fix any gate errors and rebuild.
12. **Report** the date, the Top Headlines list, and any 🔍 Unverified / ⚠️ flags,
    and confirm weather + markets were refreshed for today. There is no API cost.
    Remind the user to review, then `git add -A && git commit && git push` to
    publish (GitHub Pages updates within ~1 minute).

## Accuracy bar (non-negotiable — this is published publicly)
Never invent. Corroborate across 2+ independent sources; keep working source
links; prefer primary sources; flag rather than drop unverifiable items; withhold
internally-implausible figures. Enforce the 24-hour + dedupe rule. The build gate
will reject a malformed edition — treat its errors as blocking.
