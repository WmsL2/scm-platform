# 变更记录：GitHub CI Migration

Change ID：2026-09-03-006
Module：system-foundation
Date：2026-09-03

## Changes

- 正式主仓库从 Gitee 切换到 GitHub：WmsL2/scm-platform；
- GitHub Actions 成为正式 CI；
- 首次 CI 发现 backend pytest 缺少 DATABASE_URL；
- Backend CI 增加 MySQL 8 service 与仅 Runner 生命周期内使用的 scm_ci 临时数据库和凭据；
- CI DATABASE_URL 仅指向临时数据库，不使用任何真实 Secret；
- Frontend 从 npm install 改为 npm ci；
- CI 仅在 PR -> main 与 push -> main 运行。

## Database

未创建 Alembic Revision 或业务表。MySQL service 仅执行既有基线 Migration。

## Scope

未修改 Product、Supplier 或 Auth 的业务冻结规则。
