# Change Record: Direct Product Cost Pricing

Change ID: 2026-09-09-025
Module: catalog / supplier-quote
Date: 2026-09-09
Branch: docs/product-cost-pricing-flow
Type: Business Rule Freeze / Documentation Only

## Goal

Replace the planned independent Supplier Product Quote library with the confirmed Product current-cost workflow.

## Business Rule Changes

- The Product Master spreadsheet `cost_price` is the formal Product current cost and the current supplier quotation.
- Sprint 2 does not create `scm_supplier_product_quote`, a Quote API, Quote pages, Quote permissions, quote history, validity periods, VOID records or multi-supplier comparison.
- A future Product Backend updates the target `scm_product.cost_price` when a supplier provides a new price. The update must atomically recompute and persist all frozen derived prices and margins through the existing Pricing Service.
- Existing Product `updated_by` and `updated_at` are the audit trail for a current-cost update. `source_supplier_id` remains the import-source relationship, not a current-quote-supplier or quote-history relation.

## Documentation

- Added ADR-0009 and marked the Quote portions of ADR-0005 and ADR-0008 as superseded.
- Updated architecture, scope, roadmap, page plan, data gates, Schema Review, Agent rules and project-control module status.

## Database / Code / API / UI

No Migration, ORM, API, frontend, permission code or database data was created or changed.

## Remaining Work

- The future Category/Product Migration must include frozen `scm_product.cost_price DECIMAL(18,4) NOT NULL`, but no Quote table.
- The future Product Backend must define the cost-update endpoint and permission, validate the value and call Pricing Service in the same transaction.
- If the business later needs supplier-price history, validity periods or comparison, it requires a new ADR and implementation scope.
