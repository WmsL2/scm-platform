# Change Record: Product Import Large File Support

Change ID: 2026-09-18-001
Module: catalog / product-import / infrastructure
Date: 2026-09-18
Branch: feat/product-import-large-file-support

## Problem

实际商品大表约 500MB，但原 Product Import 固定限制 25MB，且 Router 与 Confirm 图片流程会把完整
工作簿读入内存。前端默认 10 秒请求超时只能显示“商品 Excel 预览失败”。

## Delivered

- 预览上传改为 1MB 分块落入临时文件；Service 从文件路径以只读模式解析，并在线程中执行同步
  `openpyxl` 工作。
- 默认限制调整为可配置的 1GB 文件和 100,000 数据行；保留明确的 422 文件大小/行数保护。
- ObjectStorage 增加受根目录约束的文件复制能力，含 `DISPIMG` 的临时源工作簿和 Confirm 图片提取
  均不再需要完整字节数组。
- 商品导入预览请求超时调整为 15 分钟，并改善网络/超时提示。
- 表头校验仅读取批准的前 43 列；Excel/WPS 写入到 XFD 的空白格式列不再造成模板误判，额外非空表头仍拒绝。

## Boundaries

- 不修改 43 列模板、正式 Product 字段、供应商/SKU 业务键、导入 Confirm 原子性或图片生命周期规则。
- 无数据库 Schema、Alembic Revision、权限或 API 路径变化。

## Verification

- 后端 Ruff、mypy：PASS；完整 pytest：PASS（168 passed）。
- 前端 typecheck、Vitest：PASS（86 passed）；生产构建：PASS（保留既有 Vite 大 chunk 警告）。
- Product Import 分块上传、文件路径图片提取和 LocalFileStorage 文件复制均有回归覆盖。
