# Generating editions

Even Brief has **two interchangeable generation front-ends** that both produce a
schema-valid `content/editions/<date>.json`, which `build/render.py` then turns
into the site. They share the same schema, validation gate and build.

| | **Claude Code mode** (recommended for you) | **API pipeline** |
|---|---|---|
| Backend | Claude Code (this tool) on your **subscription** | Anthropic **API** (`ANTHROPIC_API_KEY`, metered) |
| Cost | none beyond normal Claude Code usage | ~$2–3.50 per edition |
| Trigger | you ask Claude Code (interactive) | `python -m evenbrief.pipeline` / nightly GitHub Action |
| Web research | Claude Code's WebSearch / WebFetch | server-side `web_search` / `web_fetch` |
| Unattended cron | no (run it when you want) | yes (`.github/workflows/daily.yml`) |

You picked **Claude Code mode** so you don't spend API credits. The API pipeline
stays in the repo for anyone who later wants the automated nightly run — adding
the `ANTHROPIC_API_KEY` secret is the only switch.

## Claude Code mode — how to run it

In a Claude Code session **in this repo**, type:

```
/new-edition
```

(optionally `/new-edition 2026-06-22` for a specific date). That runs the
playbook in `.claude/commands/new-edition.md`: it reads the spec + schema +
`content/edition.example.json`, dedupes against `archive.json`, researches
6–10 stories with web search/fetch (neutral newswire tone, 2+ source
corroboration, fact-checks, logic flags), builds markets + Guildford weather,
writes the edition JSON, validates, and runs the build. Then review and push.

Prefer to drive it yourself? Just ask in plain English: *"research today's news
and build a new Even Brief edition."* The slash command is the same prompt,
saved.

### The authoring loop (what the build expects)

* Write **today's** edition to `content/editions/<YYYY-MM-DD>.json`, copying the
  shape of `content/edition.example.json`. `edition.archive` only needs **today's**
  items — the build merges the existing `archive.json` and strips stale `panel`
  links automatically.
* Validate the draft: `python -m evenbrief.check_edition content/editions/<date>.json`
  (clear per-field errors).
* Build + gate: `python -m build.render --edition content/editions/<date>.json`
  (writes `index.html`, `archive.json`, `template-reference.html`, refreshes
  `sitemap.xml` + README; fails with no output if the edition is malformed).
* Publish: `git add -A && git commit -m "Edition: <date>" && git push`.

## Headless / scripted Claude Code (optional)

You can also run it non-interactively with the Claude CLI on your subscription:

```bash
claude -p "/new-edition" --permission-mode acceptEdits
```

…and even put *that* on your own machine's cron if you want a hands-off daily
edition without API spend. (GitHub's hosted runners can't use your subscription,
which is why the repo's nightly Action uses the API key instead.)

## What never changes

Both front-ends end at the same place: a validated `Edition` → `build/render.py`
→ the self-contained `index.html`. The schema (`src/evenbrief/schema.py`), the
validation gate (`build/validate.py`) and the design (`templates/` + `assets/`)
are shared, so editions look and behave identically however they were generated.
