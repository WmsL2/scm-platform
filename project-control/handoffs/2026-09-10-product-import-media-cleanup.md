# Handoff: Product Import Staged Media Cleanup

状态：COMPLETED

日期：2026-09-10
来源分支：`feat/product-import`
接收范围：Catalog / Local Storage Lifecycle

## Completed

- WPS/Excel `DISPIMG` 图片已在 Product Import 预览阶段保存到项目相对目录 `local-data/files/product-images/<task-id>/`。
- `scm_product_import_row.image_storage_key` 记录暂存文件键；Confirm 后 Product 使用相同文件的 `local-media/...` 相对引用。
- 实际媒体受 `.gitignore` 隔离，不会随 Git 提交。

## Remaining Scope

- 已由 `20260914_0023` / ADR-0017 实现：预览不再保存商品图片；超过 `PRODUCT_IMPORT_UNCONFIRMED_RETENTION_DAYS` 的未完成或部分确认任务在下一次预览时标记为 `EXPIRED`，并仅清理临时源文件和未导入行媒体。
- 已确认的 Product 图片继续由 `scm_product.image_reference` 引用，明确排除在清理范围外。

## Constraints

- 不保存本机绝对路径，不把图片写入 Git。
- 清理必须先验证任务/正式 Product 的关联，不能按目录通配符盲删。
