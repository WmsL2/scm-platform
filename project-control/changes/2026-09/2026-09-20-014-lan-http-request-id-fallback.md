# Change Record: LAN HTTP Request ID Fallback

Date: 2026-09-20  
Module: web-admin / auth

## Delivered

- 修复普通 HTTP 局域网 IP 页面中浏览器不提供 `crypto.randomUUID()` 时，登录等 API
  请求在执行 `fetch` 前抛错、未产生网络请求的问题。
- 请求 ID 优先保留原生 UUID；不可用时生成仅用于请求与日志关联的回退值。
- 回退值不承担认证、授权、会话或安全令牌用途；正式部署仍应使用 HTTPS。

## Verification

- 新增前端 HTTP 客户端测试，覆盖 `crypto.randomUUID()` 不可用时仍发送请求并携带回退 ID。
- 运行前端单元测试、TypeScript typecheck 与生产 build。

## Migration

无。
