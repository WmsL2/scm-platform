# Change Record: Product Import Safety and Concurrency

Change ID: 2026-09-18-007
Module: catalog / product-import
Date: 2026-09-18
Branch: feat/product-import-safety-concurrency

## Problem

百分比原始文本可能触发 MySQL `Data truncated` 后继续写入；4,000+ 行一次返回并渲染会拖慢页面；
不同导入任务同时确认相同来源供应商 + SKU 时还存在后确认覆盖先确认结果的风险。

## Delivered

- 比例、金额、销量在预览阶段完成 Decimal/Pydantic 标准化并保存，空值写 `NULL`，非法值阻止确认。
- 明细 API 和页面改为服务端状态筛选与每页 50 行分页。
- Staging 写入按 500 行 flush；供应商名称展示和 Confirm 供应商校验改为批量查询。
- 500MB 级工作簿预览与确认图片提取受同一可配置进程内并发闸门保护，默认并发 1。
- Confirm 加入稳定锁顺序、Product 版本快照检查和数据库唯一约束兜底，冲突返回 409 而非静默覆盖。
- 新增 Revision `20260918_0033`：`normalized_data`、`target_product_id`、
  `target_product_updated_at` 及目标商品查询索引。
- Migration 对上述字段和索引执行存在性检查，兼容本分支旧临时 Revision `0031` 已在开发库执行的场景。

## Boundaries

- 不重建或删除 `scm_product_import_row`，不修改正式商品、供应商或账号数据。
- 不按 Excel 文件名或哈希合并任务；相同商品冲突以 `source_supplier_id + sku` 判断。
- 不新增 Redis/ARQ 依赖；跨进程正确性由 MySQL 锁、版本快照及 UNIQUE 约束保证。

## Verification

- Product Import / Excel image targeted pytest：13 passed。
- 完整后端、前端与迁移验证见本次结束报告。
