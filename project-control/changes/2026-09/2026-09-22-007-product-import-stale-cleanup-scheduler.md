# Change Record: Product Import Five-Hour Stale Cleanup

Date: 2026-09-22
Branch: `codex/feat/product-import-stale-cleanup`
Alembic Revision: 无

## Implementation

- 新增独立 `cleanup_stale_product_imports` 命令，默认清理创建超过五小时的 Task，每轮上限 100 条。
- 清理候选和媒体 Key 均使用投影查询，不读取暂存 Excel 行 JSON。
- 每条候选使用短事务和 `FOR UPDATE SKIP LOCKED`；临时 Excel / 未导入图片删除成功后，按 Row、SupplierMatch、Task 顺序物理删除。
- Windows 计划任务由部署服务器每 15 分钟调用该命令；本次代码不创建本机计划任务。

## Verification

- Ruff 与修改代码的 strict mypy 通过。
- 命令 `--help` 通过。
- MySQL `127.0.0.1:3307` 当前拒绝连接，依赖数据库的 Product Import API 回归待数据库恢复后执行。

