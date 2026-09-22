# Change Record: Product Import Immediate Staging Purge

Date: 2026-09-22
Branch: `codex/fix/product-import-immediate-staging-purge`
Alembic Revision: 无

## Problem

新的 Excel 预览和 Confirm 会同步遍历历史导入暂存记录，且清理实现会加载完整暂存行 JSON；历史记录较大时即使当前 Excel 很小也会延迟请求。

## Implementation

- 移除预览与 Confirm 入口中的历史暂存任务清理调用。
- 全部 Confirm 成功后，删除临时源 Excel，再按 `scm_product_import_row`、`scm_product_import_supplier_match`、`scm_product_import_task` 的顺序立即删除该批暂存数据。
- 关闭/Discard 时，删除临时源 Excel、未导入临时图片后按相同顺序立即删除该批暂存数据。
- 若临时文件删除失败，保留 Task 和精确 storage key，避免删除数据库定位信息后留下无法追踪的文件。
- 不新增计划任务；异常关闭留下的任何状态暂存数据由业务方手工清理。
- 新增显式管理员命令 `python -m app.jobs.purge_product_import_task --task-id <UUID>`；仅清理指定且默认已超过 24 小时的 Task，不扫描其他导入任务。未确认 Task 会先置为 `EXPIRED`，再按精确文件 Key 和外键顺序删除。

## Verification

- `pytest -q tests/catalog/test_product_repository.py tests/catalog/test_excel_images.py tests/catalog/test_product_import_api.py` — 36 passed.
- Ruff 覆盖修改文件通过。
- 修改的应用代码与 Repository 严格 mypy 通过；现有 `test_product_import_api.py` 有 15 个历史 mypy 错误，与本变更无关。

## API / UI / Permission

- API path、请求和 Confirm/Discard 响应 schema：不变。
- 全部 Confirm 成功或 Discard 后，`GET /api/v1/products/imports/{task_id}` 返回 404，因为该临时任务已被物理删除。
- UI 和权限：不变。
