# Change Record: Auth Real API Integration

Change ID: 2026-09-07-010
Module: auth-rbac / web-admin
Branch: feat/auth-real-api-integration

## Goal

关闭本机前端 Mock，完成 Vue、FastAPI 与 MySQL 的真实认证联调，不扩展
Refresh Token、Session、Supplier、Product 或 Business Sequence。

## Changes

- 本机 `apps/web-admin/.env` 明确设置 `VITE_USE_MOCK=false`；该本机配置不提交 Git；
- 前端认证 API 增加真实路径测试，确认 Mock 关闭时调用既有 login、me、logout 契约；
- 使用迁移完整的 MySQL 和临时随机用户完成真实 HTTP 验证，验证结束后删除临时用户；
- 更新 Auth Module Status、Sprint、CURRENT_STATUS 与 Handoff。

## API / UI / Permission

- API：未新增或变更 API；验证既有 `POST /api/v1/auth/login`、`GET /api/v1/auth/me`、
  `POST /api/v1/auth/logout`；
- UI：未新增页面；认证客户端默认使用真实 FastAPI；
- Permission：未新增权限码；验证既有 401、403 和权限撤销行为。

## Database / Alembic

Revision: 无新增。开发库已验证处于 `20260903_0002` head。

## Verification

- 真实 HTTP：login、me、stateless logout、错误密码、过期 Token、DISABLED、deleted：PASS；
- Backend：`pytest tests/auth tests/integration/test_auth_schema.py`，17 passed；
- Backend：Ruff PASS；mypy PASS；
- Frontend：`npm run test`，11 passed；`npm run typecheck` PASS；`npm run build` PASS。

## Remaining Work

Refresh Token、server-side Session、multi-device Logout 不在本任务范围；后端下一任务为
Business Sequence，Supplier 继续受字段资料 Gate 限制。
