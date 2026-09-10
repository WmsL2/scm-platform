# Handoff: Product Import Master Data Prerequisite

状态：SUPERSEDED BY ADR-0010

日期：2026-09-10
来源分支：`feat/product-import`
接收范围：Catalog / Category Source Loader（不再是本商品导入前置工作）

## Completed

- 固定 32 列商品大表的 Staging、来源供应商精确匹配、预览、人工解析和原子 Confirm 已实现；迁移更新为 `20260910_0014`。
- 正式商品只写 `source_supplier_id`，Excel 的 `supplier_name_raw` 只保存于 Import Staging。
- 用户提供的 Excel 已进行只读、事务回滚预检，未改变文件，也没有保留导入任务或商品。

## Remaining Scope

- 维护真实模板所需的 Supplier Master：候选必须是 `ARCHIVED + NORMAL + not deleted`；空供应商和没有精确同名候选的行仍须先由业务处理。
- 在上述数据准备完毕后，从商品页面重新上传、查看预览并由具有导入权限的用户 Confirm。

## Constraints

- ADR-0010 已允许固定商品大表直接保存 Excel 三级类目文字；不需要解析或写入 `scm_category`。
- 不能以供应商名称作为正式外键。
- 不能创建供应商、模糊匹配或由 AI 自动绑定。
- 任意无效行、未解析的供应商或失效的引用都必须阻止全批次 Confirm。
