# Change Record: Product Import Lock Contention Control

Date: 2026-09-22
Branch: `fix/product-import-lock-contention`
Alembic Revision: `20260922_0038`

## Problem

导入任务的机会性临时媒体清理会锁定旧 Task；历史任务较多或旧任务被事务占用时，新的单人 Excel 预览也可能等待。Confirm 在锁住 Task 后处理内嵌图片，扩大了重复 Confirm 的锁窗口。

## Implementation

- 新增 `scm_product_import_task(status, created_at)` 索引。
- 清理拆分为状态专用的有序查询，每个导入请求最多处理 100 个候选，并以 `FOR UPDATE SKIP LOCKED` 跳过被占用任务。
- Confirm 先读取可编辑任务并以独立尝试前缀准备图片文件；取得 Task 锁、完成并发复核后才写入图片键、正式 Product 与导入审计。
- Confirm 失败会删除本次准备的图片；不会删除仍待确认任务的原始 Excel。成功 Confirm、Discard 与 24 小时过期清理仍按既有规则删除临时源 Excel。

## Verification

- `pytest -q tests/catalog/test_product_repository.py tests/catalog/test_excel_images.py` — 9 passed.
- `pytest -q tests/catalog/test_product_import_api.py` — 27 passed.
- Ruff 与 mypy 覆盖修改的 Catalog 文件和测试通过。
- `alembic heads` — 单 Head：`20260922_0038`。

## API / UI / Permission

- API path and response schema: unchanged.
- UI: unchanged.
- Permission: unchanged.
