# 变更记录：Sprint 0 本机 MySQL 最终验收

Change ID：2026-09-02-003
Module：system
Date：2026-09-02

## Goal

在真实本机 MySQL 8 开发库 `zhongcheng_scm_dev` 验收 Sprint 0 Local-First 工程底座。

## Configuration Fixes

- 增加 `cryptography` 后端依赖，以支持 MySQL 8 的
  `caching_sha2_password` 认证；
- 关闭 pydantic-settings 对环境列表字段的预解码，使
  `CORS_ORIGINS=http://localhost:5173` 的逗号分隔配置可正常加载。

## Verification

- Async SQLAlchemy / asyncmy：连接成功，`SELECT 1` 返回 1；
- Alembic：唯一 head 为 `20260902_0001`，`upgrade head` 成功；
- 数据库：仅存在 `alembic_version`，值为 `20260902_0001`；
- FastAPI：`GET /health/live`、`GET /health/ready` 均返回 HTTP 200；
- Backend：pytest 4 passed、Ruff passed、mypy passed；
- Frontend：typecheck 和 production build passed。

## Database

Alembic Revision：`20260902_0001`。未创建任何 Sprint 1+ 业务表。

## Next Step

Sprint 1 — Auth/RBAC + Supplier，在新的 Feature Branch 上执行。
