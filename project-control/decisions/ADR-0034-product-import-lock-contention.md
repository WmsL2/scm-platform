# ADR-0034：商品导入清理与 Confirm 锁竞争控制

状态：ACCEPTED
日期：2026-09-22

## Context

商品导入预览和 Confirm 会机会性清理过期临时任务。旧实现用一条无上限的 `FOR UPDATE` 查询同时覆盖过期、已过期和已确认任务；在存在历史任务或其他未收尾事务时，新的单人导入也可能等待旧任务锁。Confirm 在锁定 Import Task 后提取并保存内嵌图片，使同一任务的重复 Confirm 持锁时间随图片处理时间增长。

## Decision

- 为 `scm_product_import_task(status, created_at)` 增加索引，支持按状态和过期时间查找未确认任务。
- 清理候选按任务状态分为三类查询，每次最多锁定 100 个任务，并使用 MySQL 8 `FOR UPDATE SKIP LOCKED`。已被锁定的旧任务本次跳过，由后续清理处理；不会为等待旧任务而阻塞新的导入。
- Confirm 在取得非锁定任务快照后先准备内嵌图片；随后才锁定 Task、重新校验来源供应商和 Product 版本，并将仍有效行对应的图片键写入 Staging 与正式 Product。
- 每次 Confirm 的图片准备使用独立尝试前缀；图片准备成功但 Confirm 后续冲突、过期或失败时，只清理本次新增图片键。临时源 Excel 仍只在 Confirm 成功、Discard 或 24 小时兜底过期清理时删除。

## Consequences

- 同一 Task 的并发 Confirm 仍依赖 `FOR UPDATE`、版本快照和正式 Product 唯一约束保证不重复写入；第二个请求可能在最终短事务等待或收到冲突，但不会因图片提取长期占用 Task 锁。
- 清理不再保证每次请求都处理全部过期任务；这是以导入响应时间优先的有意取舍。部署方如需严格定时清理，应使用独立调度器调用同一清理用例。
- 新增 Alembic Revision `20260922_0038`；无 API 路径、权限、Excel 模板或正式商品字段变化。

## Related

- ADR-0027 商品导入数值安全、分页与并发确认
- ADR-0029 商品导入内嵌图片逐张流式保存
- ADR-0031 商品导入临时源 Excel 保留与 24 小时清理
