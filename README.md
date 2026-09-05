# WEEKLY V0.7 — Zero-Cost Editorial

WEEKLY is a personal weekly magazine generated from RSS/Atom feeds.

## What's new in V0.7
- No OpenAI call is required to build the weekly issue.
- RSS/Atom metadata remains the source of truth.
- The fetcher enriches up to 24 selected articles by visiting their original pages and extracting:
  - Open Graph / Twitter main image when available
  - H1 headings
  - H2 headings
- The magazine uses original titles, descriptions, images and headings instead of AI-written summaries.
- The editorial JSON status is `rss` / `zero-cost`.
- Supabase source management remains unchanged.

## Optional AI later
The architecture keeps the editorial layer separate. A future version can re-enable AI behind an explicit flag (`ENABLE_AI=true`) without making the magazine depend on it.

## Install
Replace the project files in your GitHub repo with this version. **Keep your existing `config.js`**; it is intentionally not included in the ZIP.

Then run GitHub Actions → **Build WEEKLY issue** → **Run workflow**.

Check `data/articles.json` for `headings` and `image`, and `data/editorial.json` for `"status": "rss"`.
