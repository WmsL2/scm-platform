# Change Record: Product Source Supplier Resolution

Change ID: 2026-09-09-020
Module: catalog / product-import / supplier
Branch: docs/product-source-supplier-link
Type: Business Rule Change / Schema Decision

## Changes

- 替代旧规则。旧规则为：商品大表“供应商”列仅作 IMPORT_ONLY，且不产生 Product → Supplier 关系；新规则将其解析为来源供应商，并在正式 `scm_product` 中保存 `source_supplier_id`。
- 冻结 Staging `supplier_name_raw`、正式 `scm_product.source_supplier_id`、确定性名称规范化和按批次分组的 Match Decision 语义。
- 冻结 `AMBIGUOUS`、`UNMATCHED`、`INELIGIBLE` 的人工解析边界，以及 Confirm 时重新验证供应商有效状态的全批次原子门禁。
- 明确来源供应商不等于 Supplier Product Quote，Product Import 不自动创建报价。

## Database / Code

无 Migration、ORM、API、Frontend 或 Supplier Master 业务模型变更。

## Next Step

在后续 Product Import Schema/Migration 任务中，基于当时 main Head 实施并测试本 ADR 的表、约束、服务和权限设计。
