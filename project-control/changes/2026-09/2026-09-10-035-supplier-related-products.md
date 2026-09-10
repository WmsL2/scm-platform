# Change Record: Supplier Related Products

Change ID: 2026-09-10-035
Module: supplier / catalog
Date: 2026-09-10
Branch: feat/supplier-related-products

## Goal

Allow an authorized user to open the formal Product Master records supplied by the supplier currently shown on the Supplier Detail page.

## Implementation

- Product list API accepts optional UUID query `source_supplier_id` and applies the filter to both list and total-count queries.
- Supplier Detail shows a `相关商品` button only when the user has both Supplier Detail access (route guard) and `product:list` permission.
- The button opens the existing Product Master list with `source_supplier_id` in the query string. The list shows a clear active-filter notice and an explicit action to return to all products.
- Product list responses now include the existing `image_reference`; the first list column renders the saved local image as a thumbnail, with an explicit no-image or load-failed placeholder.
- This reuses the formal `scm_product.source_supplier_id` relation. No new table, migration, duplicate endpoint, or supplier/product denormalized field was created.

## Security

- The filtered Product API remains protected by `product:list`; a Supplier permission alone cannot expose Product data.

## Verification

- Product API test verifies that a filtered response contains only the requested supplier's products.
- Frontend API test verifies serialization of the supplier filter.
