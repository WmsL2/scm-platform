# 2026-09-22-007：商品 Excel 导出取消

- HTTP Client 的 JSON 与 Blob 请求支持外部 `AbortSignal`，并继续保留内部 timeout；监听器在请求结束时移除。
- 商品导出为每次请求创建独立 AbortController。取消、X 和 ESC 中止请求，取消后不创建 Blob URL 或触发下载；旧请求 finally 不会覆盖后续请求状态。
- Operation Timer 新增 `cancelled` 状态，显示“已取消，耗时”。
- 未修改 Product Export 后端同步生成：浏览器端请求会立即中止，但服务端不保证停止已开始的 CPU/图片处理。
- 无 Migration、无 Permission 变化。

## Verification

- Frontend Vitest：30 files / 130 tests passed；覆盖 Http JSON/Blob 外部取消、Product API signal、Timer cancelled 状态与页面取消绑定。
- Frontend typecheck 与 production build passed；构建仅保留既有 chunk-size warning。
