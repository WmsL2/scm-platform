# ADR-0036：商品导入超过五小时的独立暂存清理

状态：ACCEPTED
日期：2026-09-22

## Context

正常 Confirm 和 Discard 会立即删除 Staging；浏览器崩溃、断网、未完成或部分确认的导入仍可能遗留。业务要求这些 Task 自创建起超过五小时自动删除，同时不能重新把历史清理放回预览或 Confirm 请求。

## Decision

- 新增独立命令 `python -m app.jobs.cleanup_stale_product_imports --older-than-hours 5`。
- 命令只查询 Task ID、状态、创建时间、临时文件 Key 和未导入图片 Key；不得加载暂存行 JSON。
- 每轮最多处理 100 个超过五小时的 Task。每条 Task 使用短事务与 `FOR UPDATE SKIP LOCKED`；被其他事务占用的 Task 留待下一轮，避免等待锁。
- 非 `CONFIRMED` Task 在清理时标记为 `EXPIRED`；随后精确删除临时 Excel 和未导入图片，成功后按 Row、SupplierMatch、Task 的顺序物理删除。
- `CONFIRMED` Task 正常已即时删除；仅在先前临时源 Excel 删除失败时由本任务重试。正式 Product 和其图片永不删除。
- Windows 服务器用计划任务每 15 分钟调用该命令，并设置“任务正在运行时不启动新实例”。代码不在 API 进程内自行定时运行。

## Consequences

- 导入任务最多在超过五小时后的 0～15 分钟内被自动清理。
- `PARTIALLY_CONFIRMED` 超时后会删除剩余 Staging，但不会回滚已经写入正式 Product 的行。
- 临时文件删除失败时，该条 Task 留待下一轮重试，不会删除数据库定位记录。
- 无 Alembic Migration、无 API/UI/权限变更。

## Supersedes

- ADR-0035 中“不新增 Windows 计划任务或独立调度器”的决定；其“正常终态立即删除”规则仍保留。

