# 当前项目状态 / Current Project Status

项目：众诚智链商品管理平台
Repository：zhongcheng-scm-platform
Baseline：Sprint 1 Auth Kernel / Web Admin Auth Real API Integration completed
日期：2026-09-07

## Repository

- Remote：GitHub
- GitHub Repository：WmsL2/scm-platform
- Main Branch：`main`
- main：Auth Kernel 已通过 PR #6 合入；Sprint 1 继续进行
- GitHub Actions：正式 CI（PR -> main 与 push -> main）

## 当前 Sprint

Sprint 1 — Auth/RBAC + Supplier

状态：IN_PROGRESS
进度：Auth Kernel MERGED / DONE（PR #6，Merge Commit `6f229e75`）；Web Admin Auth Shell 已完成并通过真实 API 联调；后端下一任务为 Business Sequence；Supplier Master 仍受字段 Gate 限制

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

- 后端：Business Sequence 是下一任务。
- Supplier Master：继续等待真实供应商字段资料解除 Gate。

## Blocker

- Repository：无代码合并 Blocker。
- Supplier：`SUPPLIER_FIELD_DICTIONARY_PENDING_SOURCE_CONFIRMATION` 仍有效。

## Workstreams / Implementation Context

- `feat/auth-real-api-integration`：关闭 Mock 并完成真实 Auth API 联调，待合入。
- Business Sequence：由后端负责人继续推进，分支状态待同步。
- Supplier 字段资料 Gate 尚未解除。
