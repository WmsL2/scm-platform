# System Foundation

状态：COMPLETED
Owner：Sprint 0 / Sprint 0.5
Last Updated：2026-09-03（Sprint 1 design freeze）

## Database
- [x] Alembic Async 基线 Revision（无业务表）

## Backend
- [x] FastAPI、健康检查、统一响应、异常、请求 ID、日志、基础抽象
- [x] 版本化 `/api/v1` Router 基础与前端统一 HTTP Client

## Frontend
- [x] Vue 管理后台壳层、路由和 404

## Permissions
- [x] 权限依赖占位抽象（仅占位；Auth/RBAC 尚未开发）

## Tests
- [x] pytest（health/live、InlineTaskQueue、LocalFileStorage、统一响应）

## Known Issues
无。

## Sprint 0 / 0.5 Acceptance

- [x] 本机 MySQL 8 Async SQLAlchemy 连接
- [x] `alembic upgrade head` 与 `alembic_version=20260902_0001`
- [x] `/health/live`、`/health/ready` 均为 HTTP 200
- [x] pytest、Ruff、mypy、前端 typecheck/build
- [x] Settings fail-fast、全局未知异常、依赖就绪失败 503、路径安全测试

## CI

- GitHub Actions：保留为未来镜像兼容配置，未等同于 Gitee CI。
- Gitee CI：GITEE_CI_PENDING_CONFIGURATION。

## Next Step
Auth/RBAC 设计已冻结，等待 feat/auth-rbac 按 docs/09 实施；尚未创建任何 Auth 表或 API。
