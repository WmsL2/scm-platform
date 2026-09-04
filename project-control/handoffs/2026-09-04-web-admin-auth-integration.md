# Handoff: Web Admin Auth Real API Integration

日期：2026-09-04
来源分支：`feat/web-admin-auth-shell`
接收范围：Auth/Database 后端负责人完成开发库基线后，由前端继续真实接口验收。

## Completed

- 前端登录、Token、CurrentUser、路由守卫和 401/403 已实现；
- authApi 已按冻结契约封装 login、me、logout；
- 本地 Mock 模式和浏览器流程已验收；
- Mock 与真实 API 共用 Pydantic 对应的 TypeScript Schema。

## Pending

- 在 Alembic Revision `20260903_0002` 完整落库后设置 `VITE_USE_MOCK=false`；
- 创建受控开发账号，验证 login -> me -> logout；
- 验证错误密码、Token 失效、用户 DISABLED/deleted 和权限撤销后的前端行为；
- 完成后更新本 Handoff、Auth Module Status 和 Change Record，不把 Mock 结果作为真实接口结果。

## Constraints

- 不向前端暴露默认生产账号或密码；
- 不把 roles/permissions 写入前端自造 JWT；
- 前端从 `/api/v1/auth/me` 获取实时角色与权限；
- Supplier Field Gate 和 Business Sequence 不属于本 Handoff。
