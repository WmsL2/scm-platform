# Change Record: Product Latest Excel Fields

Change ID: 2026-09-09-027
Module: catalog / product
Date: 2026-09-09
Branch: feat/product-master

## Goal

Align the implemented Product schema and documentation with the confirmed latest 32-column Product Master Excel.

## Change

- Added `scm_product.selling_points TEXT NULL` for the Excel `卖点` column.
- Added `scm_product.storefront_type VARCHAR(64) NULL` for the Excel `自营旗舰店/官方旗舰店` column. Values remain source text; no enum was invented.
- Removed obsolete `remote_area_freight_note`, because the latest Excel no longer contains that column. The local Product table was verified empty before the migration.
- The latest Excel `供应商` remains a future Product Import staging field `supplier_name_raw`; formal Product continues to use `source_supplier_id` only.
- Updated the Product schema matrix and field dictionary from 31 to 32 columns.

## Explicitly unchanged

- No Product Import API or Excel template implementation is introduced by this schema alignment.
- No independent Supplier Product Quote table or current-quote-supplier relationship is introduced.

## Migration

Revision `20260909_0009`, down revision `20260909_0008`.
