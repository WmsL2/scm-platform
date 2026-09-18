# Change Record: Product Price Source Precision

Change ID: 2026-09-18-008
Module: catalog / product-import
Date: 2026-09-18
Branch: feat/product-import-safety-concurrency

## Problem

商品大表价格原值可超过 4 位小数；旧 `DECIMAL(18,4)` 和 Pydantic 限制只能拒绝或四舍五入，
无法满足原值无损保存。

## Delivered

- 六个正式价格字段从 `DECIMAL(18,4)` 扩展为 `DECIMAL(65,30)`。
- SQLAlchemy 与 Pydantic 精度同步，导入价格不按 Excel 显示格式四舍五入。
- 商品查询 API 保持至少 4 位小数的兼容格式，并完整返回第 5 位后的有效小数，移除数据库补齐的尾零。
- 新增 Revision `20260918_0034`，升级只扩大列类型；降级在可能丢失数据时中止。
- 集成测试覆盖 30 位小数价格的预览、Confirm 与数据库精确往返。

## Boundaries

- `profit` 仍为 `DECIMAL(18,4)`，按 Excel 显示精度处理公式浮点尾差。
- 比例字段仍为 4 位小数；不修改利润和比例公式规则。
- 不修改既有正式商品价格值，不引入 Float。

## Verification

- Alembic Head / Current：`20260918_0034`。
- 完整测试结果见本次结束报告。
