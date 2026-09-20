# ADR-0017：商品导入图片仅在确认时落盘

状态：ACCEPTED
日期：2026-09-14

## Context

原实现会在商品 Excel 预览阶段逐行提取 WPS/Excel `DISPIMG` 媒体。上传同一工作簿会产生新的 Task UUID 和新的本地图片，即使全部行未通过或用户未确认导入，也会持续占用本机 `local-data/files/product-images/`。

## Decision

- 预览仅检测 `DISPIMG` 公式，不写入商品图片；前端显示“确认后保存”。
- 有公式图片的预览任务保存受控的临时源 Excel 键 `source_file_storage_key`，用于供应商人工解析后继续 Confirm；它不是正式 Product 图片引用。
- Confirm 通过所有业务复核后，只为本次实际写入 `scm_product` 的通过行提取并保存图片；正式 Product 继续只保存 `local-media/<storage-key>` 相对引用。
- 全部行 Confirm 后立即删除临时源 Excel。关闭预览时作废任务并立即删除；异常关闭时，超过 `PRODUCT_IMPORT_UNCONFIRMED_RETENTION_DAYS`（默认 1 天）的未完成或部分确认任务在后续导入操作中改为 `EXPIRED`，清理临时源文件和未导入行媒体。
- 清理不得按目录通配符执行；必须由 Task/Row 的精确 storage key 驱动。任何已导入行及其 `scm_product.image_reference` 对应媒体均不得删除。

## Consequences

- Revision `20260914_0023` 新增 `source_file_storage_key` 并允许 Import Task 状态 `EXPIRED`。
- 过期任务保留 Staging 审计信息但不可继续解析或 Confirm，需重新上传。
- LocalFileStorage 新增受根目录约束的单键删除；MinIO 仍只保留抽象边界，未在本任务配置。

## Related

- ADR-0004 Local-First
- ADR-0011 商品导入本地图片存储
- ADR-0016 商品导入允许通过行分批确认
