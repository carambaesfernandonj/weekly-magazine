# WEEKLY v0.9.8 — Hard 2-Column Constraint

Built from v0.9.7 / v0.9.6 Smart Composer.

## What changed
- Article text is hard-limited to a maximum of 2 columns on desktop.
- Tablet/mobile use 1 column.
- The measured paginator now checks BOTH vertical and horizontal overflow.
- If CSS multicolumn content would spill into a third column, the candidate page is rejected and the content is moved/split onto another page.
- This prevents the third-column clipping bug seen in the reader.

## Test
Use long stories in SINGLE view first. Look for pages where text previously appeared outside the right edge. The page should now create another page instead of a third column.
