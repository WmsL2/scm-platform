# Change Record: Product Category Direct Multi-select Filter

Change ID: 2026-09-17-004  
Module: catalog  
Date: 2026-09-17  
Branch: feat/product-category-multiselect-filter

## Goal

Allow Product List users to search and select multiple categories directly at level 1, level 2, or level 3. Selecting a child must visibly include its parent levels without changing the intended result set.

## API / UI

- `GET /api/v1/products` accepts repeated `category_ids` and `category_selections` query parameters. A category selection has the form `LEVEL1:<category UUID>`, `LEVEL2:<category UUID>`, or `LEVEL3:<category UUID>`; the service resolves it against an active `MALL_LEVEL3` row and combines direct selections with OR. Other Product filters retain their existing AND composition.
- `GET /api/v1/categories/filter-options` accepts `level`, optional `keyword`, `offset`, and a bounded `limit` (1–50). It returns active mall category options in `{ items, has_more }`, each with a display label and controlled parent selection keys.
- The Product List category controls are independently remotely searchable and multi-selectable. No category options are requested when the page first opens; focus or search requests the first 50 entries, and scrolling the dropdown to its bottom appends the next batch while `has_more` is true. A changed keyword resets the option list. Level-2 options display `一级 / 二级`; level-3 options display the full three-level path to distinguish identical names.
- Scroll continuation uses both Element Plus `end-reached` and the dropdown `popup-scroll` position. The latter starts the next batch when the visible list is within 24 pixels of its bottom, so a browser that does not emit an exact end-of-scroll event still continues loading. The common loading and `has_more` guards prevent duplicate requests.
- The page preserves direct selections separately from derived display values. A directly selected level 3 automatically appears under its level 1 and level 2 controls; a directly selected level 2 automatically appears under level 1.
- The page preserves only direct selections in its query. Derived parents are not sent as extra filters.

## Database / Permission

- No schema change and no Alembic Revision.
- No permission change. The existing `product:list` permission continues to protect the Product query and both category option endpoints.

## Verification

- Web Admin targeted Vitest: `9 passed`.
- Web Admin `npm run typecheck`: PASS.
- Web Admin `npm run build`: PASS.
- Backend `ruff check app`: PASS; `mypy app`: PASS.
- Backend Catalog API integration tests: `12 passed`, including bounded remote options, offset-based continuation without duplicate rows, permission boundary, direct level-1/level-3 OR filtering, and invalid selection rejection.
- 2026-09-18 follow-up: Web Admin `npm run typecheck`, targeted category Vitest (`3 passed`) and `npm run build` passed; Catalog API pagination tests (`6 passed`) passed. The current Vite source on port 5173 and OpenAPI on port 8000 were also inspected read-only and contain the popup-scroll continuation handler and `offset` parameter respectively. A real authenticated browser scroll remains a manual acceptance item because this agent has no attached logged-in browser session.
