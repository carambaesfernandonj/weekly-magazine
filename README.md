# WEEKLY V0.5 — Persistent Sources

WEEKLY V0.5 connects the source manager to Supabase.

Architecture:

Supabase Sources → GitHub Actions → RSS/Atom → OpenAI editor → GitHub Pages

## 1. Configure the web app

Copy `config.example.js` to `config.js`.

Open `config.js` and replace:

- `supabaseUrl` with your Supabase Project URL.
- `supabaseAnonKey` with your Supabase **Publishable key** (`sb_publishable_...`).

Do **not** put a Supabase Secret key (`sb_secret_...`) here.

`config.js` is intentionally a frontend configuration file. The publishable key is designed for browser code; RLS controls what it can do.

## 2. GitHub Actions secrets

In GitHub:

Settings → Secrets and variables → Actions → New repository secret

Create:

`OPENAI_API_KEY`
`SUPABASE_URL`
`SUPABASE_SECRET_KEY`

For `SUPABASE_SECRET_KEY`, use a Supabase Secret key (`sb_secret_...`). Never put it in `config.js` or any frontend file.

## 3. What V0.5 does

- My Sources reads feeds directly from Supabase.
- `+ ADD SOURCE` stores a new RSS/Atom feed in Supabase.
- `REMOVE` deletes a feed from Supabase.
- `REFRESH` reloads the live list.
- GitHub Actions reads enabled sources from Supabase before fetching RSS.
- If the Supabase secrets are not configured in Actions, the RSS script falls back to `data/feeds.json`.
- The existing OpenAI editorial step remains unchanged.

## 4. Security note

This first V0.5 prototype uses the existing public/anonymous RLS policies you created for `sources`, so the source-management UI is intentionally simple. Anyone who can access the public app and its publishable key can exercise whatever the `anon` policies allow.

For a personal prototype this is acceptable for testing, but the next hardening step should be Supabase Auth + `authenticated` RLS policies before treating the app as a public service.

## 5. Supabase keys

Supabase now recommends:

- Publishable key → browser/frontend.
- Secret key → server/CI/backend only.

Do not expose the Secret key.
