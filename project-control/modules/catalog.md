# 商品主数据 / Catalog

状态：SCHEMA_FINALIZATION_COMPLETE / MIGRATION_PREFLIGHT_REQUIRED
Owner：TBD
Last Updated：2026-09-09

## Database
- [ ] 未开始

## Backend
- [ ] 未开始

## Frontend
- [ ] 未开始

## Permissions
- [ ] 未开始

## Tests
- [ ] 未开始

## Known Issues
- 当前环境有商品大表 `京东大表-礼品.xlsx`，但未提供“商城三级品类维表数据.xlsx”及“工业品产品线.xlsx”。商品大表缺少 Category external ID、source type 等维表字段，尚不能完成 Category UNIQUE 约束的真实数据预检。
- Product / Category 删除策略和除已冻结字段外的最终业务必填规则尚未得到业务决策；不得在 C1 Migration 自行补充删除列或强行收紧 NULL。

## Next Step
Schema Finalization 已完成；下一步是 Pricing Service，并在取得真实类目源数据、完成 UNIQUE 预检后创建 Category / Product Migration。Database / Backend / Frontend 尚未实施。

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
- 已确认商城三级品类维表与工业品产品线两类来源及扣点规则；实际维表文件尚待提供并完成预检。蓝色三级类目扣点 5%，其余当前规则 8%；
- Pricing Rule 已冻结：Decimal、4 位小数；前端可计算并提交，后端必须按正式类目规则重算校验；
- 派生价格与毛利字段需要正式保存；一期建议当前价格及派生值直接承载于 `scm_product`；
- 31 列大表字段映射、Category 三级维度建议、Product ↔ Category FK 与 Decimal 类型建议见 `docs/schema/product-category-pricing-schema-review.md`；
- 普通金额与比率使用 Decimal `ROUND_HALF_UP`、4 位小数；唯一例外 `deduction_review` 使用 `ROUND_DOWN`、4 位小数；本阶段不实现 Pricing Service。

## Current Gate

`SCHEMA_FINALIZATION_COMPLETE`：数据库结构决策已收口，但 Category UNIQUE 约束仍须用两份真实类目源数据完成预检。下一步为 Pricing Service → 数据预检 → 基于届时最新 main Alembic Head 的 Category/Product Migration → Product Backend。尚未创建 Migration、ORM、API 或页面，不得标记为已实现。
