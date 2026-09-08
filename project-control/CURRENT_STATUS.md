# 当前项目状态 / Current Project Status

项目：众诚智链商品管理平台
Repository：zhongcheng-scm-platform
Baseline：Sprint 1 Auth Kernel / Web Admin Auth Real API Integration merged; Supplier Delete & Import and Account / Registration / Profile verified; post-merge P1 hardening verified
日期：2026-09-08

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
进度：Auth Kernel DONE；Web Admin Auth DONE / REAL API VERIFIED；Business Sequence DONE / IMPLEMENTED（Revision `20260907_0003`）；Supplier Master Backend DONE / MERGED via PR #13（Revision `20260907_0004`）；Supplier Delete & Import Patch MERGED / IMPLEMENTED（Revision `20260908_0005`）；Account / Registration / Profile IMPLEMENTED / VERIFIED（Revision `20260908_0006`）；Post-Merge P1 Transaction / Validation Hardening VERIFIED（无 Migration）。当前 Alembic 迁移链为单 Head：`20260907_0004` → `20260908_0005` → `20260908_0006`。分支与合入状态以 GitHub / `main` 历史为准。

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

- 主任务：推进 Product / Category / Pricing 后续设计与实现工作；Product / Category Migration 尚未创建。
- 后续任务：在已冻结的 Product / Category / Pricing 规则基础上，安排 Pricing Service、Category / Product Migration 与 Product Backend。
- Auth 后续范围：Refresh Token、Session、Multi-device Logout 与 Role Create/Delete policy 仍待后续冻结。

## Blocker

- Repository：无代码合并 Blocker。
- Supplier：Delete & Import 已合入；未确认的企业、税务、地址、银行、资质等字段仍不得自行添加。资质业务字段及其 API 继续冻结。
- Product / Catalog：尚未创建 Product / Category Migration，需先完成 Schema Design。

## Workstreams / Implementation Context

- Auth Real API Integration：已完成真实 Auth API 联调；分支与合入状态以 GitHub / `main` 历史为准。
- Business Sequence：`sys_biz_sequence` Migration、并发安全取号服务与 MySQL 并发测试已完成；分支与合入状态以 GitHub / `main` 历史为准。
- Supplier：Backend MERGED / Frontend REAL_API_IMPLEMENTED；Delete & Import Patch MERGED / IMPLEMENTED（Revision `20260908_0005`），新增逻辑删除、`supplier:delete`、Excel 模板/校验预览/确认导入和 Web Admin 控制。
- Auth/RBAC：Auth Sprint 1 当前范围 IMPLEMENTED / VERIFIED（Revision `20260908_0006`），包括注册审批、用户角色/角色权限管理、动态权限目录、Profile 与修改密码；Refresh Token、Session、Multi-device Logout 仍属未来范围。
- Post-Merge Hardening：Request transaction ownership、Service caller-owned transaction participation、Account association ID 幂等去重与 Supplier UUID Router validation 已验证；ADR-0007 冻结事务规则，无 Migration 变化。
- Catalog：`SCHEMA_DESIGN_READY`；Product / Category Migration 尚未创建。
