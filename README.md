# WEEKLY v0.9.13 — Fast deterministic reader

Fixes the Reader freeze caused by DOM-based pagination measurements.

## Reader
- No `scrollHeight` / `scrollWidth` pagination loop.
- No DOM measurement while composing pages.
- Explicit 1- or 2-column packing based on conservative character budgets.
- Long blocks split by words; content is never intentionally discarded.
- Reader opens with a loading screen, then caches the generated page model.
- Desktop Single view uses two explicit columns; narrower views use one.

## Content fallback
The frontend uses `contentBlocks`, then `contentText`, then `description` when available. The RSS workflow should still be run to regenerate enriched article bodies.
