# Sprint 1 Supplier Delete & Excel Import

状态：已在 `fix/supplier-delete-import` 实现；PR 合并前不属于 `main`。

## 逻辑删除

`DELETE /api/v1/suppliers/{id}` 需要 `supplier:delete`。它不会物理删除任何供应商、联系人、资质或合作状态历史；而是写入：

- `scm_supplier.is_deleted = true`
- `deleted_by`、`deleted_at` 和既有 `updated_by` 审计字段
- 该供应商下仍活跃的联系人、资质记录同步逻辑删除

正常列表、详情和未来有效供应商筛选均默认过滤已删除供应商。前端只在当前用户拥有 `supplier:delete` 时展示删除按钮；后端仍强制权限校验，未授权请求返回 403。

## Excel 导入

模板仅含已冻结的五列，表头必须完全匹配：

| 供应商名称 | 主营品牌 | 主要优势 | 联系人 | 联系电话 |
|---|---|---|---|---|

- 供应商名称、主营品牌、主要优势必填；联系人和联系电话可空。
- 仅接受 `.xlsx`，最大 5 MB、最多 1,000 个非空数据行；不接受公式单元格。
- 来源旧供应商编码、来源状态文本及任何未冻结字段不会被保存或映射。
- 上传先创建 `scm_supplier_import_batch` 和 `scm_supplier_import_row` 暂存记录，返回逐行校验结果；存在错误行时不能确认。
- 只有上传该批次的同一用户才能确认；确认只能执行一次。
- 确认导入在一个事务中为每条有效行调用 `BusinessSequenceService` 生成不可回收的 `supplier_code`，并创建 `ARCHIVED + NORMAL` 的正式供应商。

前端在供应商列表页提供“下载模板”“导入 Excel”、错误预览表和“确认导入”按钮；导入不是静默入库。
