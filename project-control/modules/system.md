# System Foundation

状态：COMPLETED
Owner：Sprint 0 / Sprint 0.5
Last Updated：2026-09-04（Web Admin Auth Shell）

## Database
- [x] Alembic Async 基线 Revision（无业务表）

## Backend
- [x] FastAPI、健康检查、统一响应、异常、请求 ID、日志、基础抽象
- [x] 版本化 `/api/v1` Router 基础与前端统一 HTTP Client

## Frontend
- [x] Vue 管理后台壳层、路由和 404
- [x] 登录页、认证状态、路由守卫、403、工作区 Tab 和统一 HTTP 错误处理（实现分支：`feat/web-admin-auth-shell`）

## Permissions
- [x] Auth/RBAC 权限依赖已通过 PR #6 合入；前端 Route Meta 只负责交互控制，后端权限依赖仍是安全边界

## Tests
- [x] pytest（health/live、InlineTaskQueue、LocalFileStorage、统一响应）
- [x] 前端 Vitest、typecheck、build，并在 CI 中执行

## Known Issues
无。

## Sprint 0 / 0.5 Acceptance

- [x] 本机 MySQL 8 Async SQLAlchemy 连接
- [x] `alembic upgrade head` 与 `alembic_version=20260902_0001`
- [x] `/health/live`、`/health/ready` 均为 HTTP 200
- [x] pytest、Ruff、mypy、前端 typecheck/build
- [x] Settings fail-fast、全局未知异常、依赖就绪失败 503、路径安全测试

## CI

- GitHub Actions：正式 CI，运行 PR -> main 与 push -> main。
- Backend CI 使用 GitHub Runner 生命周期内临时 MySQL 8 服务和临时凭据；
  不使用本机、开发或生产 Secret。

## Next Step
后端继续 Business Sequence；前端在迁移完整的开发库上联调 login/me/logout；Supplier 仍受字段 Gate 限制，未开始业务实现。
