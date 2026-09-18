# ADR-0018：商品导入强制绑定商城三级类目

状态：SUPERSEDED BY ADR-0026

> 2026-09-18 起不再适用于 Product Master：`scm_product.category_id` 与
> `scm_product_import_row.category_id` 已由 Migration `20260918_0032` 删除。类目维表保留，
> 但不再是商品导入或编辑的受控关联来源。
日期：2026-09-15

## 背景

历史 Product Import 按 ADR-0010 直接保存 Excel 的三级类目文本，导致历史商品的 `category_id` 为 `NULL`，无法以受控类目关系取得正式扣点。商城三级品类维表已写入 `scm_category`，因此后续导入必须建立受控类目关联。

## 决策

- 固定商品大表导入以 Excel 的一级、二级、三级类目文本作为查询条件，仅在 `source_type = MALL_LEVEL3` 且 `is_active = TRUE` 的 `scm_category` 中精确匹配。
- 只有唯一有效匹配才可通过预览校验；将匹配的 `scm_category.id` 保存到 Staging 行的 `category_id`。
- 无匹配、仅匹配到停用类目、或匹配到多个有效类目时，该行必须标为不通过并显示原因；不得猜测、模糊匹配或任意选取一个类目。
- Confirm 必须在同一事务中重新锁定并验证 Staging `category_id` 仍是有效商城类目；正式 Product 写入该 ID，以及由该类目记录取得的一级、二级、三级名称。
- Excel 的价格、毛利、折扣率和价格虚高比例仍按 ADR-0010 直接保存；本 ADR 不触发 Pricing Service 重算或覆盖这些正式 Excel 值。
- 对任何已有 `category_id IS NULL` 的历史商品，可执行一次受控回填。每条均须唯一匹配有效商城三级类目；未满足该条件或当前库中不存在候选记录时不得更新。

## 结果

后续 Product Import 的通过行必然拥有有效 `category_id`，并可在后续成本价更新时按正式 Category 取得扣点。历史回填不重新导入 Excel，不改变供应商、SKU、价格或其他业务字段，并须在目标数据库中逐条预检后执行。

## Supersedes

替代 ADR-0010 中“Product Import 不加载、不解析、不校验 `scm_category`，也不以类目路径生成 `category_id`”及“`category_id` 不是 Confirm 前置条件”的部分；ADR-0010 关于 Excel 价格直接保存的决策继续有效。
