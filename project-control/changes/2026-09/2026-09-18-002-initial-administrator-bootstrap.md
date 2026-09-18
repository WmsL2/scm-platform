# Change Record: Initial Administrator Bootstrap

Change ID: 2026-09-18-002
Module: system / auth / deployment
Date: 2026-09-18
Branch: feat/product-import-large-file-support

## Delivered

- 环境变量首次部署管理员初始化、`boss` 角色创建和全部有效权限授予。
- 已存在或已删除的同名账号不会被重建，支持后续删除初始管理员。
- `.env.example`、本机部署文档、状态和 ADR 同步更新。

## Verification

- Ruff、mypy：PASS。
- 初始化管理员单元/集成测试：PASS。

## Boundaries

- 无 Migration、公开 API 或普通注册审批流程变化。
