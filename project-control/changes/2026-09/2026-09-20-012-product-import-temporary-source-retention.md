# Change Record: Product Import Temporary Source Retention

Change ID: 2026-09-20-012
Module: catalog / product-import
Date: 2026-09-20
Branch: feat/product-import-confirm-reupload

## Problem

用户不希望每次 Confirm 都重新选择同一份含内嵌图片的商品 Excel，但也不希望该文件长期留在本地。

## Delivered

- 含 `DISPIMG` 的预览恢复保存受控临时源 Excel；Confirm 直接提取图片并在成功后立即删除。
- 新增 `POST /api/v1/products/imports/{task_id}/discard`；关闭预览弹窗时作废任务并立即删除临时源文件。
- 将默认未确认任务保留期统一为 1 天（24 小时）；异常关闭时在后续导入操作中清理到期任务。
- 不含内嵌图片的 Excel 不保存源文件，Confirm 保持直接提交。

## Boundaries

- 不删除正式 Product、Supplier、已确认图片或历史 Staging 数据。
- 不改变供应商 + SKU 锁、版本冲突检查、分页、逐张图片流式解码和 Confirm 事务原子性。
- 浏览器关闭只是即时清理的优化；部署方若需要精确到时清理，应配置独立调度器。

## Verification

- 后端测试覆盖临时源文件 Confirm 和 discard 后源文件键清空。
- 前端 API 测试覆盖 discard 请求；类型检查、全量测试和生产构建通过。
