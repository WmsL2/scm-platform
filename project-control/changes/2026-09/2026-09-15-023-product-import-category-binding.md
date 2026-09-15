# Change Record: Product Import Category Binding

Change ID: 2026-09-15-023
Module: catalog / product-import
Date: 2026-09-15
Branch: feat/product-import-category-binding

## Goal

Require Product Import to bind every passing Excel row to one active mall level-3 Category, and repair the corresponding controlled relation on historical Products created by the former direct-text import rule.

## Delivered

- Preview resolves each Excel level-1, level-2, and level-3 path against active `MALL_LEVEL3` Category records.
- A missing, inactive, or ambiguous Category leaves the row unbound and shows a row-level rejection reason.
- Confirm revalidates and locks each resolved Category, then writes the Category ID and Category-owned path fields to Product.

## Verification

- Product Import API tests cover unique binding plus missing, inactive, and ambiguous Category rejection.
- 历史回填事务会先验证每条候选记录。当前配置开发库在实际执行时 `scm_product` 为 0 条，因此没有执行任何历史商品更新；待恢复目标历史数据后必须重新预检并回读确认。

## Boundaries

- No new table, Alembic revision, API endpoint, UI control, or permission is added.
- Import continues to save the confirmed Excel price fields directly under ADR-0010.
- Historical rows are not re-imported and no Supplier, SKU, price, or other Product business field is changed.
