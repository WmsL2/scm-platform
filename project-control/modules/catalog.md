# 商品主数据 / Catalog

状态：SCHEMA_FINALIZATION_COMPLETE / MIGRATION_PREFLIGHT_REQUIRED
Owner：TBD
Last Updated：2026-09-09

## Database
- [ ] 未开始

## Backend
- [x] Pricing Service（定价服务）已实现
- [ ] Product Backend（商品后端）未开始

## Frontend
- [ ] 未开始

## Permissions
- [ ] 未开始

## Tests
- [x] Pricing Unit Tests（定价单元测试）已完成
- [ ] Product / Catalog Integration Tests（商品目录集成测试）未开始

## Known Issues
- Category Source Data Preflight 已完成；商城 external ID UNIQUE 预检通过，工业品完整路径已按导入去重规则收口。尚未创建 Category / Product Migration。
- Product / Category 删除策略和除已冻结字段外的最终业务必填规则尚未得到业务决策；不得在 C1 Migration 自行补充删除列或强行收紧 NULL。

## Next Step
Schema Finalization、Pricing Service 与 Category Source Data Preflight 均已完成；下一步基于届时最新 Alembic Head 创建 Category / Product Migration → Product Backend → 后续 Product Import。Category / Product Database、Product Backend 与 Frontend 尚未实施。

## 已冻结业务规则
- 商品大表是正式商品主数据来源；
- 大表一行 = 一条具体商品；
- 正式商品表核心为 `scm_product`；
- `scm_product.source_supplier_id CHAR(36) NOT NULL`、索引并 FK → `scm_supplier.id ON DELETE RESTRICT`；非唯一且仅表示商品大表来源供应商；
- `scm_product.category_id CHAR(36) NOT NULL`；正式 Confirm 必须完成类目解析，Product 通过该关系取得 `deduction_rate`；
- 一期不强制 SPU/SKU；
- 真实整理后商品大表已取得；系统 `id` 为商品主键；
- `sku`、`model`、`product_name`、`brand + model`、货号、69码均不设业务 UNIQUE；
- 69码按源文本原样保存，不拆分；
- 类目来源规则已冻结为“商城三级品类维表”和“工业品产品线”两类；真实数据预检已完成：商城 `UNIQUE(source_type, level3_external_id)` 通过，商城同名称路径不同 external ID 不得被全局路径 UNIQUE 约束；工业品完整路径仅作导入去重规则。蓝色三级类目扣点 5%，其余当前规则 8%；
- Pricing Rule 已冻结：Decimal、4 位小数；前端可计算并提交，后端必须按正式类目规则重算校验；
- `cost_price` 是商品当前成本价，也是当前供应商报价；供应商新报价不进入独立报价库，而是在后续 Product Backend 直接更新目标 Product 的 `cost_price`；
- 成本价更新必须在同一事务内重算并保存派生价格与毛利，使用既有 `updated_by`、`updated_at` 审计；不保存 Quote 历史、有效期、作废或多供应商比价；
- 派生价格与毛利字段需要正式保存；一期建议当前价格及派生值直接承载于 `scm_product`；
- 31 列大表字段映射、Category 三级维度建议、Product ↔ Category FK 与 Decimal 类型建议见 `docs/schema/product-category-pricing-schema-review.md`；
- Pricing Service 已实现：使用 Decimal，正式派生值统一 4 位小数；普通字段使用 `ROUND_HALF_UP`，唯一例外 `deduction_review` 使用 `ROUND_DOWN`；该 Service 仅产生 System Calculated Values。Excel Derived Values 的逐字段对账属于后续 Product Import；Excel 值不得静默覆盖系统公式。

## Current Gate

`SCHEMA_FINALIZATION_COMPLETE / MIGRATION_PREFLIGHT_REQUIRED`：Pricing Service、核心关系与价格结构决策、Category Source Data Preflight 均已完成；删除策略和其余业务必填规则仍待业务决定。下一 Gate 为基于届时最新 Alembic Head 的 Category/Product Migration → Product Backend → 后续 Product Import。尚未创建 Category/Product Migration、Product ORM、Product API 或 Product Frontend，不得标记为已实现。
