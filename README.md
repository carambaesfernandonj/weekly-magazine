# WEEKLY V0.6 — Personal Editorial Edition

WEEKLY is a personal AI-generated magazine powered by RSS/Atom feeds, Supabase and GitHub Actions.

## What's new in V0.6
- AI editorial treatments for selected stories: headline, dek, summary, why-it-matters and key points.
- Personal editorial DNA: **Fernando Mode** (curious, informal, sharp, skeptical of hype, with restrained humor).
- Magazine reader now renders a real cover spread plus one editorial spread per selected story.
- Original source remains available via `READ ORIGINAL`.
- More robust OpenAI error reporting in GitHub Actions.
- Fixes the previous editorial schema so the AI output can actually be generated instead of silently falling back.

## GitHub Actions secrets
- `OPENAI_API_KEY`
- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`

## Supabase
The web app uses the publishable key in `config.js` for reading/writing personal sources. Keep any Supabase secret key only in GitHub Actions secrets.

## Important
The editorial text is generated as an original synthesis from the metadata/descriptions supplied by the feeds. WEEKLY does not reproduce full source articles. The original source link is always available.
