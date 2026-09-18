# ADR-0025：商品导入数值安全、分页与并发确认

状态：ACCEPTED
日期：2026-09-18

## Context

商品大表可超过 4,000 行并包含约 500MB 图片。导入链路还必须处理两类独立风险：Excel 的比例
文本不能直接交给 MySQL 数值列；多个用户的不同导入任务也可能同时命中相同的
`source_supplier_id + sku`，不能以后确认者静默覆盖先确认者。

## Decision

- Staging 保留原始单元格，同时新增 `normalized_data`。预览先把所有正式数值转换为 Decimal 并通过
  `ProductUpdateRequest` 校验；Confirm 只读取该标准化值，不把原始字符串交给 ORM/MySQL。
- 带 `%` 的比例按百分数除以 100，例如 `46.25% -> 0.4625`；不带 `%` 的比例按数据库小数值解释。
  空值为 `NULL`；非法文本、利润中的 `%`、没有缓存结果的数值公式均使该行不通过。
- 预览明细由数据库按状态分页，默认首屏 50 行；任务汇总计数仍覆盖整个工作簿。
- 重型工作簿解析和 Confirm 图片提取共用进程内资源闸门，默认每个 API 进程同时执行 1 个，可用
  `PRODUCT_IMPORT_MAX_CONCURRENT_WORKBOOKS` 调整。其他请求等待资源，不复制整份文件到内存。
- 预览更新行保存目标 Product ID 和 `updated_at`。Confirm 锁定 Task 后，按稳定顺序锁定有效供应商、
  业务键命中的 Product 和类目，并比较预览快照。预览后发生新增、修改或删除均返回
  `PRODUCT_IMPORT_STALE_PREVIEW`（409），要求重新上传预览。
- 数据库 `UNIQUE(source_supplier_id, sku)` 继续作为最终创建冲突保护。系统不通过文件名或文件哈希
  判断“同一 Excel”；并发冲突判断以正式业务键及 Product 版本为准。

## Consequences

- 新增 Revision `20260918_0031`，仅扩展 Staging 行，不修改正式商品、供应商或账号。
- 已在旧版本生成、且将更新现有 Product 的未确认任务没有版本快照，升级后须重新上传预览。
- 数据库锁与版本检查对多 API 进程仍有效；进程内重任务数量限制按进程计算，部署多个 Worker 时应
  按机器容量配置每个 Worker 的值。独立分布式任务队列不属于本次变更。
- Confirm 仍维持“本次所有当前通过行一个事务”的业务原子性。

## Related

- ADR-0016 商品导入允许通过行分批确认
- ADR-0020 商品重新导入更新正常同键商品
- ADR-0022 商品大表大文件导入
- ADR-0024 商品价格字段独立维护
