# System Foundation

状态：FOUNDATION_COMPLETED / BUSINESS_SEQUENCE_IMPLEMENTED
Owner：Sprint 0 / Sprint 0.5 / 人员 A
Last Updated：2026-09-07（Business Sequence）

## Database
- [x] Alembic Async 基线 Revision（无业务表）
- [x] `sys_biz_sequence` Revision `20260907_0003`：UUID CHAR(36)、唯一 sequence_key、前缀、递增值与审计字段
- [x] Migration 初始化 `SUPPLIER` 序列，首个编号为 `SUP00000001`

## Backend
- [x] FastAPI、健康检查、统一响应、异常、请求 ID、日志、基础抽象
- [x] 版本化 `/api/v1` Router 基础与前端统一 HTTP Client
- [x] BusinessSequence Repository + Service：同一事务内使用 `SELECT FOR UPDATE` 分配不可复用的业务编号

## Frontend
- [x] Vue 管理后台壳层、路由和 404
- [x] 登录页、认证状态、路由守卫、403、工作区 Tab 和统一 HTTP 错误处理（实现分支：`feat/web-admin-auth-shell`）

## Permissions
- [x] Auth/RBAC 权限依赖已通过 PR #6 合入；前端 Route Meta 只负责交互控制，后端权限依赖仍是安全边界

## Tests
- [x] pytest（health/live、InlineTaskQueue、LocalFileStorage、统一响应）
- [x] MySQL 集成测试：Schema、受控序列、连续取号、唯一约束与 20 并发独立 Session 取号
- [x] 前端 Vitest、typecheck、build，并在 CI 中执行

## Known Issues
- 本机 MySQL 为 8.0.12，不提供 `information_schema.check_constraints` 视图；Auth Schema 测试在该能力可用时才验证 CHECK 元数据及非法值拒绝，其余 Schema 合同始终验证。正式 CI 仍使用 MySQL 8 服务。

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
Business Sequence 已可供后续 Supplier Master 调用；分支与合入状态以 GitHub / `main` 历史为准。Supplier Field Gate 解除后再开始 Supplier Master 实现。
