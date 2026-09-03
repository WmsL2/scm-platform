# 变更记录：Sprint 0.5 Foundation Hardening

Change ID：2026-09-03-004
Module：system-foundation
Date：2026-09-03

## Goal

在不进入 Sprint 1、且不创建业务表的前提下，加固 Sprint 0 底座。

## Changes

- `DATABASE_URL` 改为 Settings 必填项，示例改为专用开发账号占位；
- 增加安全的未知异常响应和完整服务端异常日志；
- readiness 在数据库或已启用的可选依赖不可用时返回 HTTP 503；
- 建立 `/api/v1` Router 基础，以及前端唯一 HTTP Client 入口；
- 增加跨平台换行策略；
- 修正文档中的 Git、Alembic 路径、Sprint 状态、System Foundation 定义及 Gitee CI 状态。

## Database

Alembic Revision：无新增。未创建任何业务表。

## Verification

- pytest：13 passed；
- Ruff、mypy：passed；
- Frontend typecheck、production build：passed。

## CI

Gitee CI：`GITEE_CI_PENDING_CONFIGURATION`。GitHub Actions 文件仅为未来镜像兼容保留。

## Next Step

停止于 Sprint 0.5；获得明确授权后才进入 Sprint 1。
