# Change Record: Product Import Confirm Timeout and Key Batching

Change ID: 2026-09-18-010
Module: catalog / product-import
Date: 2026-09-18
Branch: feat/product-import-safety-concurrency

## Problem

4,000+ 行 Confirm 的正式 Product 业务键查询构造了一个超大的
`(source_supplier_id, sku) IN (...)` 条件，触发 MySQL 默认 8MB
`range_optimizer_max_mem_size` 警告并增加执行时间。前端 HTTP 默认等待 10 秒，后端继续提交成功时页面却会误报“确认导入失败”。

## Delivered

- Product 业务键查询与 `FOR UPDATE` 锁定按稳定顺序每 500 组分批执行。
- Confirm 保持同一事务、版本检查和唯一约束保护；分批不允许静默覆盖并发导入。
- Product Import Confirm 浏览器请求超时调整为 15 分钟；预览和普通 API 的默认超时不变。
- 增加 Repository 批查询回归测试和前端 API 超时契约测试。

## Boundaries

- 无数据库 Schema、API 路径、权限或 Alembic 变化。
- 不重放、不改写历史 Import Task；已部分确认的行保持 `is_imported`，不重复导入。
