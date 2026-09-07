# WEEKLY v0.9.7 — Measured Smart Composer

This build continues v0.9.6 and keeps the weekly RSS window, Supabase source sync, single-page reader and multi-image enrichment.

## What changed

- Replaces character-only pagination with browser-measured pagination for article pages.
- Measures each candidate page against the actual fixed page geometry before accepting another content block.
- Long blocks are split into smaller chunks when necessary.
- Continuation images are included in the same measurement budget, so an image cannot push text below the page.
- If an image plus the next block does not fit, the composer can defer the image rather than clipping content.
- The final page is rebalanced to leave room for the END OF STORY / READ ORIGINAL footer.
- Inline article images use `object-fit: contain` so the source photo itself is not intentionally cropped.
- The existing Single / Spread reader remains available; Single remains the recommended validation mode.

## Important

The compositor is still zero-AI / zero-credit. It uses the browser's actual layout engine to decide what fits.
