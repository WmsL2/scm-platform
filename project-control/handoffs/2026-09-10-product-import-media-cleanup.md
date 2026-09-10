# Handoff: Product Import Staged Media Cleanup

状态：OPEN

日期：2026-09-10
来源分支：`feat/product-import`
接收范围：Catalog / Local Storage Lifecycle

## Completed

- WPS/Excel `DISPIMG` 图片已在 Product Import 预览阶段保存到项目相对目录 `local-data/files/product-images/<task-id>/`。
- `scm_product_import_row.image_storage_key` 记录暂存文件键；Confirm 后 Product 使用相同文件的 `local-media/...` 相对引用。
- 实际媒体受 `.gitignore` 隔离，不会随 Git 提交。

## Remaining Scope

- 为长期未 Confirm 的导入预览任务定义并实现媒体清理策略，例如按任务状态、保留天数和 Product 正式引用排除条件清理。
- 在实现清理前，绝不能删除 Confirm 后仍被 `scm_product.image_reference` 引用的图片。

## Constraints

- 不保存本机绝对路径，不把图片写入 Git。
- 清理必须先验证任务/正式 Product 的关联，不能按目录通配符盲删。
