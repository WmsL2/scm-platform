# ADR-0031：商品导入临时源 Excel 保留与 24 小时清理

状态：ACCEPTED
日期：2026-09-20

## Context

含 WPS/Excel `DISPIMG` 内嵌图片的商品导入需要在 Confirm 时从原工作簿逐张提取媒体。要求用户再次选择相同 Excel 虽不长期保留文件，但会让一次数千行导入多一步人工操作。

## Decision

- 仅含 `DISPIMG` 的预览任务在 `product-import-sources/<task-id>.xlsx` 保存临时源文件；无内嵌图片的任务不保存该文件。
- Confirm 直接使用该临时源文件提取本次实际写入 Product 的图片，所有通过行提交成功后立即删除源文件。
- 前端关闭导入预览时调用 `POST /api/v1/products/imports/{task_id}/discard`；后端将任务置为 `EXPIRED` 并按精确 storage key 删除源文件及未导入行临时媒体。
- 浏览器异常关闭、断网、进程中断等无法收到 discard 请求的情况，以 `PRODUCT_IMPORT_UNCONFIRMED_RETENTION_DAYS=1`（24 小时）兜底。到期任务在后续导入操作中被置为 `EXPIRED` 并清理；不得删除已导入 Product 引用的图片。

## Consequences

- 用户对正常预览可直接点击一次“确认新增/更新”，不需要重复选择 Excel。
- 临时 Excel 最长可能保留到下一次导入操作触发过期清理；部署方如需严格定时删除，应通过独立调度器调用同一清理用例，不能依赖浏览器关闭事件。
- 本变更复用既有 `source_file_storage_key`、`EXPIRED` 状态和 Storage abstraction，无 Alembic Migration。

## Related

- ADR-0017 商品导入图片仅在确认时落盘
- ADR-0022 商品大表分块上传与磁盘只读解析
- ADR-0029 商品导入内嵌图片逐张流式保存
