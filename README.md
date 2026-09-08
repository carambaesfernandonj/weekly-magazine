# WEEKLY v0.9.18 — AI Editorial + Issue Lock + Spanish UI

## Issue lock
- Each Sunday→Saturday issue is generated once and then locked.
- Re-running GitHub Actions for the same editorial window keeps the existing editorial, cover and story selection.
- Set `FORCE_REGENERATE_ISSUE=true` only when intentionally rebuilding an issue.

## AI, zero-cost fallback
- If `OPENAI_API_KEY` works, the build makes at most one text generation and one image generation for the issue.
- Text uses `gpt-5.6-luna` by default and writes the opening editorial in Fernando Mode.
- Cover uses `gpt-image-2` with the early-2000s magazine direction.
- If either call fails or no credits/key are available, WEEKLY falls back to the static manifesto and `assets/weekly-cover-fallback.svg`.
- Generated results are stored in `data/editorial.json` and `data/covers/issue-N.png`; opening the site never calls the API.

## Language
- App UI and editorial/magazine chrome are Spanish.
- Article titles, excerpts and source content remain in their original language.

## Reader
- Full articles use the stable v0.9.17 single-column reader.
- Short-source items are grouped under Noticias breves.
