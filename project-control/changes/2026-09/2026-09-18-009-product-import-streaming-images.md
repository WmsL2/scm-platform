# Change Record: Product Import Streaming Images

Change ID: 2026-09-18-009
Module: catalog / product-import
Date: 2026-09-18
Branch: feat/product-import-safety-concurrency

## Problem

旧图片提取器对整本工作簿使用 50MB 累计内存上限，达到上限后直接停止，导致大表 Confirm 成功但后续商品没有图片；浏览器也不能直接可靠展示 TIFF/EMF 等媒体。

## Delivered

- 预览阶段校验每个 `DISPIMG` 引用的媒体存在性、支持类型和单图大小；无效引用按行阻止确认。
- Confirm 打开工作簿 ZIP 一次并逐张流式提取、解码和保存，移除整本工作簿图片累计上限。
- TIFF/EMF/BMP/WMF 转 PNG；PNG/JPEG/GIF/WebP 保持原格式。
- 新增 `PRODUCT_IMPORT_MAX_IMAGE_MB=64`，限制单张图片而不是整批图片总量。
- 测试覆盖流式提取、格式转换、缺失引用、旧累计上限回归及 Confirm 图片暂存。

## Boundaries

- 不补图、不改写历史 Product 或 Staging 数据；用户重新上传并 Confirm 后应用。
- 图片列为空仍允许导入；只有存在公式引用却无法取得有效图片时才判失败。
- 无 API 路径、权限或数据库 Schema 变化，无 Alembic Revision。

## Verification

- 用户真实大表：4,356 个公式引用、4,220 个唯一图片，全部逐张解码成功，失败 0。
- 完整自动化测试结果见本次结束报告。
