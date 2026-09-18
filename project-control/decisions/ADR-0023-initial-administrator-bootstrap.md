# ADR-0023：首次部署管理员初始化

状态：ACCEPTED
日期：2026-09-18

## Context

普通注册账号一律为 `PENDING`，必须由已有管理员审批。全新部署若没有预置管理员，会出现首个注册账号无人审批的死锁。

## Decision

- 部署环境可同时设置 `INITIAL_ADMIN_USERNAME`、`INITIAL_ADMIN_PASSWORD`。
- 应用启动时，在数据库 Migration 已完成的前提下创建已启用的内置 `boss` 账号，并将所有当前有效权限授予 `boss`。
- 创建成功后应移除两个环境变量。若同名账号已存在，包含逻辑删除账号，初始化不更新、不复活、不重建该账号；因此后续可按常规流程删除此管理员。
- 任一变量缺失、用户名为空/超长或密码少于 8 位时启动失败，避免半配置部署。

## Consequences

- 不新增公开 API、角色权限或 Migration。
- 生产部署必须先执行 `alembic upgrade head`，再启动 API。

## Related

- ADR-0004 Local-First
- ADR-0016 Auth Session Refresh
