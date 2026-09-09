# 商品主数据 / Catalog

状态：SCHEMA_REVIEW_READY
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
无。

## Next Step
Product / Category / Pricing Schema Review 已完成，等待评审冻结结构；Database / Backend / Frontend 尚未实施。

## 已冻结业务规则
- 商品大表是正式商品主数据来源；
- 大表一行 = 一条具体商品；
- 正式商品表核心为 `scm_product`；
- `scm_product` 推荐新增非唯一的 `source_supplier_id CHAR(36) NOT NULL`，索引并 FK → `scm_supplier.id ON DELETE RESTRICT`；其含义仅为商品大表来源供应商；
- 一期不强制 SPU/SKU；
- 真实整理后商品大表已取得；系统 `id` 为商品主键；
- `sku`、`model`、`product_name`、`brand + model`、货号、69码均不设业务 UNIQUE；
- 69码按源文本原样保存，不拆分；
- 已取得商城三级品类维表与工业品产品线两份类目来源；蓝色三级类目扣点 5%，其余当前规则 8%；
- Pricing Rule 已冻结：Decimal、4 位小数；前端可计算并提交，后端必须按正式类目规则重算校验；
- 派生价格与毛利字段需要正式保存；一期建议当前价格及派生值直接承载于 `scm_product`，等待 Schema Review 确认；
- 31 列大表字段映射、Category 三级维度建议、Product ↔ Category FK 与 Decimal 类型建议见 `docs/schema/product-category-pricing-schema-review.md`；
- 普通金额与比率使用 Decimal `ROUND_HALF_UP`、4 位小数；唯一例外 `deduction_review` 使用 `ROUND_DOWN`、4 位小数；本阶段不实现 Pricing Service。

## Current Gate

`SCHEMA_REVIEW_READY`：Database Schema Review 已完成，等待后续 Runtime Implementation。下一步为 Pricing Service → 基于届时最新 main Alembic Head 的 Category/Product Migration → Product Backend。尚未创建 Migration、ORM、API 或页面，不得标记为已实现。
