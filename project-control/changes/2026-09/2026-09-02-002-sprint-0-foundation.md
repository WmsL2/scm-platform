# 变更记录：Sprint 0 Local-First 企业底座

Change ID：2026-09-02-002
Module：system
Date：2026-09-02

## Goal

从零建设 FastAPI + Vue 的 Local-First 企业工程底座，不引入业务模块或业务表。

## Changes

- 建立 Monorepo、FastAPI 异步 SQLAlchemy/MySQL 配置与 Async Alembic；
- 增加请求 ID、结构化日志、统一响应、全局异常、健康检查和 OpenAPI 元数据；
- 增加 TaskQueue、ObjectStorage、Cache、审计、权限、业务编号和幂等抽象；
- 默认使用 InlineTaskQueue 和 LocalFileStorage；ARQ、Redis、MinIO 仅为可选适配器边界；
- 增加 Vue 3 + TypeScript strict + Element Plus + Pinia + Router 的后台壳层；
- 增加 Windows/macOS/Linux 本机脚本、基础 CI 和测试。

## Database

Alembic Revision：`20260902_0001`。该 Revision 只建立迁移基线，不创建业务表。

## Product Master Guardrail

未创建 `scm_product`、`scm_import_*`、`scm_product_sku` 或任何供应商、报价、商品业务表。
商品大表仍是正式商品主数据来源；真实字段和唯一键待后续数据字典冻结。

## Remaining Work

MySQL 实例需由每位开发者本机准备后运行 ready 检查与迁移。

## Next Step

Sprint 1 在独立 Feature Branch 实现 Auth/RBAC 与供应商模块。
