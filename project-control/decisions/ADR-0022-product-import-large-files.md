# ADR-0022：商品大表大文件导入

状态：ACCEPTED
日期：2026-09-18

## Context

商品大表会包含大量商品图片，实际工作簿可达到约 500MB。此前 Product Import 在 Router 中
调用 `UploadFile.read()`，Service 又从 `BytesIO` 打开两次工作簿，并固定拒绝超过 25MB 的文件。
这会导致正常的大表在预览前被拒绝，或因浏览器 10 秒超时显示笼统失败。

## Decision

- Product Import 上传按 1MB 分块写入操作系统临时文件，不把完整 Excel 读入 Python 内存。
- 预览从文件路径以 `openpyxl` 只读模式打开工作簿；同步解析放入工作线程，避免阻塞 FastAPI
  事件循环。
- 默认最大文件为 1GB、最大数据行为 100,000；通过 `PRODUCT_IMPORT_MAX_FILE_MB` 和
  `PRODUCT_IMPORT_MAX_ROWS` 配置，部署可按硬件容量收紧。
- 含 `DISPIMG` 的源文件由 ObjectStorage 的文件复制能力受控保存；Confirm 复制到临时文件后
  按路径提取图片，继续遵守 ADR-0017 的确认后落盘和过期清理规则。
- Product Import 预览请求前端超时设为 15 分钟，并保留服务端具体错误消息。

## Reason

大文件的主要风险是整文件内存副本、长时间同步解析和网络上传时间，而不是业务模板规则。
文件路径、只读解析和可配置资源边界能支持当前 500MB 级大表，同时不取消服务器的容量保护。

## Consequences

- 不新增表、权限、Migration 或 AI 行为。
- 本机和生产反向代理仍必须允许对应的请求体大小与读取超时；部署文档明确此要求。
- 超过 1GB 或 100,000 行仍返回可识别的 422 错误，不静默截断或部分入库。

## Related

- ADR-0004 Local-First
- ADR-0011 商品导入图片本地存储
- ADR-0017 商品导入图片仅在确认时落盘
