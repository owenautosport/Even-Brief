# Even Brief

> **AI disclosure:** Even Brief is researched, written and fact-checked by an AI system from public, non-paywalled sources. AI can make mistakes — verify anything important independently. Not financial, legal or medical advice.

A self-contained daily news briefing (one HTML file): top stories with fact-checks,
confidence ratings and media-framing analysis, plus markets, live stocks, a full
weather page and a searchable archive.

## How it's published
This folder is the website. `index.html` is the whole site.
Hosted on GitHub Pages (static, free, HTTPS).

## To update the site
Replace `index.html` with the newest edition and commit. The live site updates
within ~1 minute.

## Notes
- Most of the page works offline; the live stock widgets (TradingView) and the
  rain radar (Leaflet + RainViewer) need an internet connection to load.
- `.nojekyll` tells GitHub Pages to serve files as-is.
