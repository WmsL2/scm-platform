# 商品主数据 / Catalog

状态：SCHEMA_DESIGN_READY
Owner：TBD
Last Updated：2026-09-07

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
商品、类目及价格字段门禁已冻结，可进入 Product Master Schema Design；Database / Backend / Frontend 尚未实施。

## 已冻结业务规则
- 商品大表是正式商品主数据来源；
- 大表一行 = 一条具体商品；
- 正式商品表核心为 `scm_product`；
- 一期不强制 SPU/SKU；
- 真实整理后商品大表已取得；系统 `id` 为商品主键；
- `sku`、`model`、`product_name`、`brand + model`、货号、69码均不设业务 UNIQUE；
- 69码按源文本原样保存，不拆分；
- 已取得商城三级品类维表与工业品产品线两份类目来源；蓝色三级类目扣点 5%，其余当前规则 8%；
- Pricing Rule 已冻结：Decimal、4 位小数；前端可计算并提交，后端必须按正式类目规则重算校验；
- 派生价格与毛利字段需要正式保存，最终 Product/Pricing Schema 结构留待评审。

## Current Gate

`SCHEMA_DESIGN_READY`：商品主数据的正式字段设计可开始，但尚未创建 Product / Category Migration、ORM、API 或页面，不得标记为已实现。
