# ADR-0035：商品导入终态立即删除暂存数据

状态：ACCEPTED
日期：2026-09-22

## Context

导入预览和 Confirm 曾机会性清理历史暂存任务。该清理为判断临时媒体加载命中 Task 的全部导入行及 JSON，在历史数据较大时会延迟新的 Excel 导入。业务方不要求保留已完成或已关闭导入的逐行预览、校验结果和供应商匹配记录，也不采用 Windows 计划任务。

## Decision

- 用户关闭预览或放弃未完成导入时，先按精确 storage key 删除临时源 Excel 与未导入行临时图片；删除成功后，在同一短事务中按 `Row -> SupplierMatch -> Task` 的外键顺序物理删除该批暂存数据。
- 全部 Confirm 成功时，先删除临时源 Excel；删除成功后立即按相同外键顺序物理删除该批暂存数据。已写入正式 Product 的图片不会删除。
- `PARTIALLY_CONFIRMED` 不属于终态，仍保留尚未处理的行；用户关闭该预览时才整体删除。
- 文件删除失败时保留对应 Task/Key，避免丢失重试定位信息；业务方可人工清理异常遗留数据。
- 预览和 Confirm 不再触发任何历史 Task 清理，不新增 Windows 计划任务或独立调度器。
- 手工命令仅按明确指定的 Task UUID 工作，默认要求 Task 已创建至少 24 小时。未确认的异常遗留 Task 会先标记为 `EXPIRED` 再清理；不得以清理名义删除正式 `scm_product`、`scm_supplier` 或正式商品图片。

## Consequences

- 正常成功和关闭流程不再累计 Staging 行，新的导入请求不会因历史暂存数据清理而读取大量 JSON。
- 已成功 Confirm 的导入不能再通过导入预览 API 查询逐行结果；正式 Product 的创建/更新审计和商品数据仍保留。
- 浏览器崩溃、断网或进程中断后未收到关闭请求的 Task 不会自动过期；业务方可显式运行单 Task 人工清理命令，默认只允许清理已创建 24 小时以上的 Task。
- 本变更不修改表结构，无 Alembic Migration。

## Supersedes

- ADR-0031 中“24 小时后在后续导入操作中自动过期清理”的规则。
- ADR-0034 中“预览和 Confirm 机会性清理历史 Task”的规则；其中 Confirm 缩短持锁窗口的并发控制仍保留。
