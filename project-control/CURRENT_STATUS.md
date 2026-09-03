# 当前项目状态 / Current Project Status

项目：众诚智链商品管理平台
Repository：zhongcheng-scm-platform
Baseline：Sprint 0 stable baseline
日期：2026-09-03

## Repository

- Remote：Gitee
- Branch：`main`
- main：Sprint 0 stable baseline
- Gitee CI：GITEE_CI_PENDING_CONFIGURATION（GitHub Actions 仅保留镜像兼容）

## 当前 Sprint

Sprint 0 — Local-First 企业项目底座

状态：COMPLETED
进度：100%

## 已冻结

- [x] FastAPI 唯一业务后端
- [x] Vue 3 管理后台
- [x] MySQL 8
- [x] Alembic
- [x] Local-First
- [x] Docker 非 Sprint 0 必需
- [x] Multi-Developer / Multi-Agent
- [x] 文档同步 Definition of Done
- [x] 供应商编码系统自动生成
- [x] 供应商产品报价独立历史库
- [x] 商品大表是正式商品主数据来源
- [x] 大表一行 = 一条具体正式商品
- [x] 一期不强制 SPU/SKU
- [x] scm_product 最终字段等待真实大表数据字典冻结

## 下一步

Sprint 1 — Auth/RBAC + Supplier（在新的 Feature Branch 上执行）。

## Blocker

无。2026-09-02 已在本机 MySQL 8 开发库 `zhongcheng_scm_dev` 完成
Async SQLAlchemy 连接、`alembic upgrade head` 与 health readiness 验收。

## Active Branches

无。
