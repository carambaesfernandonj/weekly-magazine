# WEEKLY V0.8.1 — Zero-Cost Editorial

Personal RSS/Atom magazine reader. V0.8 does not require OpenAI credits.

## This Week
Instead of manually selecting individual stories, choose editorial tags. WEEKLY builds a candidate pool from matching stories and randomly selects up to 24 with category diversity. Use SHUFFLE to regenerate the selection.

Tags are generated from feed category plus article title/description and the extractor's keyword taxonomy. The article list is now a preview of the pool, not a manual checklist.

## Setup
1. Keep your existing `config.js` with the Supabase publishable key.
2. Run GitHub Actions → **Build WEEKLY issue**.
3. Open the site and go to **This Week**.
4. Pick tags, shuffle if desired, then generate the magazine.

The pipeline remains RSS/Atom → dedupe → scoring → tag enrichment → bounded page enrichment (image/H1/H2) → magazine. No AI call is made.


## V0.8 — Real Magazine
WEEKLY now uses several magazine page layouts (feature, news, image-led, shorts), a table of contents, clickable cover stories, page numbering, source imagery/headings and original-source links. The editorial layer remains zero-cost and source-first.

## V0.8.1 — Custom Topics
This Week now supports persistent custom topics in addition to automatically detected tags. Custom topics search titles, descriptions, H1/H2, source names and existing tags. Common shortcuts include ANIME, MARVEL, DC, RETRO GAMING, POKEMON and STAR WARS. No OpenAI credits are required.

## V0.8.3 — Magazine rhythm
- Print-inspired cover treatment and issue header.
- Stronger editorial typography, running heads and page metadata.
- More pronounced magazine/spread visual hierarchy.
- Keeps V0.8.1 custom topics and zero-cost RSS editorial flow.
