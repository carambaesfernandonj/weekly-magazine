# WEEKLY V0.7 — Zero-Cost Editorial

Personal RSS/Atom magazine reader. V0.7 does not require OpenAI credits.

## This Week
Instead of manually selecting individual stories, choose editorial tags. WEEKLY builds a candidate pool from matching stories and randomly selects up to 24 with category diversity. Use SHUFFLE to regenerate the selection.

Tags are generated from feed category plus article title/description and the extractor's keyword taxonomy. The article list is now a preview of the pool, not a manual checklist.

## Setup
1. Keep your existing `config.js` with the Supabase publishable key.
2. Run GitHub Actions → **Build WEEKLY issue**.
3. Open the site and go to **This Week**.
4. Pick tags, shuffle if desired, then generate the magazine.

The pipeline remains RSS/Atom → dedupe → scoring → tag enrichment → bounded page enrichment (image/H1/H2) → magazine. No AI call is made.
