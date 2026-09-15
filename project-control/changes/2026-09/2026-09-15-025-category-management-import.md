# Change Record: Category Management and Import

Change ID: 2026-09-15-025
Module: catalog
Date: 2026-09-15
Branch: main (local working tree)

## Delivered

- Added management APIs and a Catalog menu/page for the existing `scm_category` level-3 dimension, reusing `product:list`, `product:update`, and `product:import` permissions.
- Added template-backed `.xlsx` import. Rows are validated first against the real `UNIQUE(source_type, level3_external_id)` identity; identical existing rows skip, and all new rows are inserted in one transaction.
- No Category schema, migration, or permission seed was changed. `scm_category` is a fixed three-level path dimension, not an adjacency-list tree: this module does not provide mutable parent-child topology, arbitrary-depth trees, node moves, sorting or soft deletion. A dynamic tree requirement needs a separate Schema Design Change.
