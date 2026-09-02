# 系统基础 / Auth & RBAC

状态：COMPLETED
Owner：Sprint 0
Last Updated：2026-09-02

## Database
- [x] Alembic Async 基线 Revision（无业务表）

## Backend
- [x] FastAPI、健康检查、统一响应、异常、请求 ID、日志、基础抽象

## Frontend
- [x] Vue 管理后台壳层、路由和 404

## Permissions
- [x] 权限依赖占位抽象（RBAC 待 Sprint 1）

## Tests
- [x] pytest（health/live、InlineTaskQueue、LocalFileStorage、统一响应）

## Known Issues
无。

## Sprint 0 Final Acceptance

- [x] 本机 MySQL 8 Async SQLAlchemy 连接
- [x] `alembic upgrade head` 与 `alembic_version=20260902_0001`
- [x] `/health/live`、`/health/ready` 均为 HTTP 200
- [x] pytest、Ruff、mypy、前端 typecheck/build

## Next Step
Sprint 1 实现 Auth/RBAC、审计和业务编号的正式持久化能力。
