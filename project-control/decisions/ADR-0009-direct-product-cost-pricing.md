# ADR-0009：商品当前成本价承载当前供应商报价

状态：ACCEPTED
日期：2026-09-09

## Context

业务确认商品大表中的 `cost_price` 就是该具体商品的当前供应商报价。当前一期不需要多供应商报价对比、报价有效期、报价作废或独立报价历史。

## Decision

- 不创建 `scm_supplier_product_quote`，不建设独立 Supplier Product Quote 模块、API、页面、权限或历史表；
- 正式 `scm_product.cost_price` 是当前成本价，也是当前供应商报价；
- 商品大表 Confirm 时将经校验的成本价写入正式 Product；
- 供应商新报价由后续 Product Backend 直接更新目标 Product 的 `cost_price`；同一事务内必须调用冻结的 Pricing Service，重新计算并保存全部派生价格和毛利字段；
- 成本价更新使用 Product 的既有 `updated_by`、`updated_at` 审计字段；不额外假设报价供应商、有效期、历史版本或多供应商关系；
- `source_supplier_id` 继续仅表示商品大表来源供应商，不是当前报价供应商；
- 需要独立报价历史、多供应商比价或报价有效期时，必须重新进行业务确认并新增 ADR。

## Reason

将当前成本价和当前商品价格计算集中在 `scm_product`，符合“一行商品大表 = 一条具体正式商品”的已冻结来源，避免为当前未确认的报价历史和比价能力提前设计表与流程。

## Consequences

- Sprint 2 的 Supplier Product Quote 规划取消，替换为 Product Cost Pricing；
- Product Migration 不包含 Quote 表；
- 后续 Product Backend 必须提供受控的成本价更新与派生价格原子重算；
- 系统不具备历史报价回溯或多供应商价格比较能力。

## Related

- ADR-0005（部分替代）
- ADR-0008（来源供应商规则继续有效）
- `docs/schema/product-category-pricing-schema-review.md`
