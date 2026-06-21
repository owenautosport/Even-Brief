# Even Brief — Automation & Operations

## What runs, and when

| Workflow | Trigger | Does |
|---|---|---|
| `.github/workflows/daily.yml` | ~06:30 Europe/London daily + **Run workflow** button | generate today's edition → build the site → commit if changed |
| `.github/workflows/ci.yml` | every push / PR | run the test suite + a build-gate check (no API key) |

Cron is UTC, so `daily.yml` has **two** schedules — `30 5 * * *` (06:30 BST) and
`30 6 * * *` (06:30 GMT) — and a guard step lets through only the one where the
local London hour is `06`. Manual `workflow_dispatch` runs always proceed.

## One-time setup

### 1. Add the `ANTHROPIC_API_KEY` secret  ← **required before the first run**

The generation backend calls the Anthropic API and reads the key from the
environment. Add it as a repository secret:

> **GitHub → your `Even-Brief` repo → Settings → Secrets and variables →
> Actions → New repository secret**
> - **Name:** `ANTHROPIC_API_KEY`
> - **Secret:** your key from <https://console.anthropic.com/settings/keys>
> - **Add secret**

The key is metered/paid. **Rough cost ≈ $2–3.50 per daily run** (≈90–110 web
searches at ~$0.01 each, plus Sonnet research/writing and a compact Opus
verification pass). The exact figure per run is printed by the pipeline's
`CostMeter` and scales with how many stories and searches the day needs.

### 2. Enable GitHub Pages

> **Settings → Pages → Build and deployment → Source: Deploy from a branch →
> Branch: `main` / root.** The live site is
> <https://owenautosport.github.io/Even-Brief/>. `.nojekyll` is already present
> so files serve as-is.

### 3. Allow Actions to push

`daily.yml` declares `permissions: contents: write`. Also ensure
**Settings → Actions → General → Workflow permissions** is set to
**Read and write permissions**.

## Running it

* **On demand:** Actions tab → *Daily edition* → **Run workflow**.
* **Locally (dry-run, no key, no network):**
  ```bash
  python -m evenbrief.pipeline --dry-run --out content/editions/test.json
  python -m build.render --edition content/editions/test.json --check-only
  ```
* **Locally (real edition, needs the key):**
  ```bash
  export ANTHROPIC_API_KEY=sk-ant-...
  python -m evenbrief.pipeline --out content/editions/$(date +%F).json
  python -m build.render --edition content/editions/$(date +%F).json
  ```

## Changing the schedule

Edit the two `cron:` lines in `daily.yml`. To keep the 06:30-London behaviour
across DST, move **both** lines by the same offset and keep the `06` guard. To
run at a fixed UTC time instead, use a single cron and delete the gate step.

## Pausing

* **Temporarily:** Actions tab → *Daily edition* → **⋯ → Disable workflow**.
* **In code:** comment out the `schedule:` block (the **Run workflow** button
  still works for manual editions).

## Adding a breaking-news cadence later

The generate → build → commit shape is reusable. Copy the `build` job in
`daily.yml`, change the schedule to e.g. `*/30 * * * *`, drop the 06:xx gate,
and run the pipeline behind a significance/dedupe gate so it only commits when a
genuinely new, material story clears the bar. No other piece changes.

## Failure behaviour

The build's **validation gate** fails the run (non-zero exit, no commit) if an
edition is malformed: unparseable HTML, missing components, palette drift,
broken/duplicated archive JSON, a sourceless story, a non-open-licence image, or
a story that repeats an older archive headline. A failed run leaves the live
site untouched — the previous good edition stays published.
