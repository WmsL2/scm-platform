# 当前项目状态 / Current Project Status

项目：众诚智链商品管理平台
Repository：zhongcheng-scm-platform
Baseline：Sprint 1 Auth Kernel / Web Admin Auth Real API Integration merged; Business Sequence implemented
日期：2026-09-07

## Repository

- Remote：GitHub
- GitHub Repository：WmsL2/scm-platform
- Main Branch：`main`
- main：Sprint 1 已包含 Auth Kernel 与 Web Admin Auth Real API Integration；后续开发继续进行
- GitHub Actions：正式 CI（PR -> main 与 push -> main）
- Feature Branch、PR、Merge SHA 与合入时间以 GitHub / `main` 历史为事实来源，不在状态文档中重复维护。

## 当前 Sprint

Sprint 1 — Auth/RBAC + Supplier

状态：IN_PROGRESS
进度：Auth Kernel DONE；Web Admin Auth DONE / REAL API VERIFIED；Business Sequence DONE / IMPLEMENTED（Revision `20260907_0003`），已可供 Supplier Master 使用；Supplier Field Dictionary 已冻结并可进入 Schema Design。分支与合入状态以 GitHub / `main` 历史为准。

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
- [x] 真实供应商字段资料与 Supplier Field Dictionary 已冻结
- [x] 真实整理后商品大表字段边界已冻结
- [x] Product / Category / Pricing Schema Design Ready

## 下一步

- 主任务：Supplier Master Schema Design / Schema Review / Migration 与 Backend 实施。
- 并行任务：Product / Category / Pricing Schema Design。

## Blocker

- Repository：无代码合并 Blocker。
- Supplier：无整体字段资料 Gate；未确认的企业、税务、地址、银行、资质等字段仍不得自行添加。Supplier Migration 必须在 Schema Review 后创建。
- Product / Catalog：尚未创建 Product / Category Migration，需先完成 Schema Design。

## Workstreams / Implementation Context

- Auth Real API Integration：已完成真实 Auth API 联调；分支与合入状态以 GitHub / `main` 历史为准。
- Business Sequence：`sys_biz_sequence` Migration、并发安全取号服务与 MySQL 并发测试已完成；分支与合入状态以 GitHub / `main` 历史为准。
- Supplier：`FIELD_FREEZE_READY_FOR_SCHEMA_DESIGN`；Database / Backend / Frontend 尚未实施。
- Catalog：`SCHEMA_DESIGN_READY`；Product / Category Migration 尚未创建。
