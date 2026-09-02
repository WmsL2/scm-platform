# Sprint 00：Local-First 企业底座

状态：COMPLETED

## Todo

- [x] Monorepo
- [x] Vue 3 Admin
- [x] FastAPI
- [x] SQLAlchemy Async
- [x] Alembic
- [x] MySQL configuration
- [x] Settings
- [x] Logging
- [x] Request ID
- [x] Global Exception
- [x] Unified Response
- [x] Pagination base
- [x] Permission abstraction
- [x] Audit abstraction
- [x] Sequence abstraction
- [x] TaskQueue abstraction
- [x] InlineTaskQueue
- [x] ObjectStorage abstraction
- [x] LocalFileStorage
- [x] Redis/ARQ adapter skeleton
- [x] MinIO adapter skeleton
- [x] Health
- [x] Windows start scripts
- [x] Unix start scripts
- [x] pytest
- [x] Ruff
- [x] typecheck
- [x] Frontend build
- [x] CI
- [x] project-control sync

## 禁止

- [ ] 不开发 Supplier 业务
- [ ] 不开发 Catalog 业务
- [ ] 不创建全量业务表
- [ ] 不强制 SPU/SKU
- [ ] 不要求 Docker

## Acceptance

- [x] Backend本机启动
- [x] Frontend本机启动
- [x] health/live 200
- [x] health/ready 200（MySQL正常）
- [x] Alembic upgrade head
- [x] pytest PASS
- [x] Ruff PASS
- [x] Typecheck PASS
- [x] Frontend build PASS
- [x] InlineTaskQueue test PASS
- [x] LocalFileStorage test PASS
- [x] 文档同步

## Final Local-First Acceptance

2026-09-02 已在本机 MySQL 8 的 `zhongcheng_scm_dev` 完成最终验收：
`20260902_0001` 是唯一 head，升级后只存在 `alembic_version` 表；
FastAPI 的 `/health/live` 与 `/health/ready` 均返回 HTTP 200。
