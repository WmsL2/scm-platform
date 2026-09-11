# Change Record: Product Logical Delete and Fixed Sidebar

Change ID: 2026-09-11-017  
Module: catalog  
Date: 2026-09-11  
Branch: feat/supplier-initial-archive-status

## Goal

Add a safe product deletion action to the Product List, keep the original page-level scrolling behavior, and keep the left navigation visible while the page scrolls.

## Delivered

- Added `DELETE /api/v1/products/{product_id}` protected by `product:delete`.
- Added logical-delete audit fields and filters so deleted products are hidden from list/detail/edit/cost-update operations.
- Added the permission seed and automatic system-administrator role grant in Revision `20260911_0019`.
- Added a permission-controlled delete button with a confirmation dialog to the Product List.
- Restored the Product List to normal page-level scrolling and fixed the left navigation to the viewport.

## Verification

- Catalog API tests cover permission enforcement, deletion, audit fields and post-delete invisibility.
- Frontend API tests, typecheck and production build cover the delete request and the adjusted page layout.

## Boundaries

- This is not a physical delete and does not remove local image files or import audit rows.
- A deleted Product still retains its source-supplier + SKU key; no restore or reimport-replacement behavior is added.
