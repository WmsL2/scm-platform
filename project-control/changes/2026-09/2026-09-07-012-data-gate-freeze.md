# Change Record: Supplier / Product Data Gate Freeze

Change ID: 2026-09-07-012
Module: supplier / catalog / product-import / category-pricing  
Branch: docs/data-gate-freeze

## Changes

- 确认真实供应商来源字段，冻结系统生成的 `supplier_code`；联系人及电话非必填，现有供应商首次导入为 `ARCHIVED + NORMAL`。
- 确认整理后的商品大表字段边界：商品使用系统 id，型号/SKU/品牌型号/商品名称/货号/69码均不设业务唯一约束，69码原样保存。
- 确认商城三级类目维表与工业品产品线来源；蓝色三级类目扣点 5%，其他当前规则 8%。
- 冻结 Pricing Rule：Decimal、4 位小数、类目扣点快照和所有派生价格/毛利公式。
- 前端可计算并提交派生值；后端必须按类目数据重算和校验；计算字段需要正式保存。

## Database

无 Migration；无 Schema change。

## Code

无业务代码变化。

## Tests / Verification

本任务为文档与数据设计冻结：检查 Markdown 内容一致性、Project Control Gate，以及 Git Diff 格式。未创建 Supplier/Product Migration、ORM 或业务实现。
