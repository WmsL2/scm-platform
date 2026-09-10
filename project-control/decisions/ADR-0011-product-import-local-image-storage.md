# ADR-0011：商品导入图片使用项目相对本地存储

状态：ACCEPTED
日期：2026-09-10

## 决策

- 固定商品大表的 WPS/Excel `DISPIMG` 图片从工作簿内嵌媒体提取，使用项目 `ObjectStorage` 抽象保存。
- Local-First 默认目录为项目根目录下的 `local-data/files/product-images/`；路径配置相对项目根目录解析，不依赖开发者用户名或磁盘绝对路径。
- 实际媒体文件受 `.gitignore` 隔离；仓库只保留 `local-data/.gitkeep` 占位，不提交商品图片。
- Staging 保存 `image_storage_key`，正式 Product 保存 `local-media/<storage-key>` 站内相对引用；FastAPI 的 `/local-media/` 路由在本机开发提供媒体文件。
- 未找到有效内嵌图片时仅产生预览警告，不能用公式文本或任意本机绝对路径替代图片引用。

## 结果

开发者克隆项目后可在自己的 `local-data/` 中独立保存和查看导入图片，不会把本机媒体写入 Git。预览但未 Confirm 的任务可能留下已忽略的图片文件，清理策略留给后续任务。
