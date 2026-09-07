# Handoff: Web Admin Auth Real API Integration

状态：COMPLETED

日期：2026-09-04
来源分支：`feat/web-admin-auth-shell`
接收范围：Auth/Database 后端负责人完成开发库基线后，由前端继续真实接口验收。

## Completed

- 前端登录、Token、CurrentUser、路由守卫和 401/403 已实现；
- authApi 已按冻结契约封装 login、me、logout；
- 本地 Mock 模式和浏览器流程已验收；
- Mock 与真实 API 共用 Pydantic 对应的 TypeScript Schema。
- 开发环境明确设置 `VITE_USE_MOCK=false`；前端认证客户端已验证使用真实
  `/api/v1/auth/login`、`/me`、`/logout`。
- MySQL Revision `20260903_0002` 上完成真实 HTTP 验证：login、me、logout、错误密码、
  过期 Token、DISABLED 与 deleted；临时用户已清理。
- 权限拒绝及权限撤销通过 MySQL 集成测试验证；前端权限路由守卫测试通过。

## Remaining Scope

Refresh Token、server-side Session、multi-device Logout 均不在已冻结的 Sprint 1
Auth Kernel 范围内，留待后续正式授权。

## Constraints

- 不向前端暴露默认生产账号或密码；
- 不把 roles/permissions 写入前端自造 JWT；
- 前端从 `/api/v1/auth/me` 获取实时角色与权限；
- Supplier Field Gate 和 Business Sequence 不属于本 Handoff。
