# Change Record: Dashboard Live Statistics

Change ID: 2026-09-16-004
Module: dashboard / catalog / supplier
Date: 2026-09-16
Branch: feat/dashboard-live-statistics

## Delivered

- Added authenticated `GET /api/v1/dashboard/summary` for formal-product and archived-supplier counts.
- Replaced the two corresponding Dashboard placeholders with live FastAPI data and explicit loading or failure state.
- Added API integration coverage for count semantics and frontend API coverage.
- Corrected collapsed-sidebar alignment so its logo, navigation icons, and version label remain centered; navigation icons use their menu item's exact 50% center instead of component default spacing, and hidden group titles no longer occupy the compact view.

## Boundaries

- Formal products follow the visible active Product-list conditions: active product plus normal, non-deleted source supplier.
- Archived suppliers include archived suppliers regardless of cooperation status, but exclude logical deletion.
- No schema, migration, permission, supplier quotation, or pending-import changes.
