# 当前项目状态 / Current Project Status

项目：众诚智链商品管理平台
Repository：zhongcheng-scm-platform
Baseline：Sprint 1 Auth Kernel / Web Admin Auth Real API Integration merged; Supplier Delete & Import and Account / Registration / Profile verified; post-merge P1 hardening verified
日期：2026-09-10

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
进度：Auth Kernel DONE；Web Admin Auth DONE / REAL API VERIFIED；Business Sequence DONE / IMPLEMENTED（Revision `20260907_0003`）；Supplier Master Backend DONE / MERGED via PR #13（Revision `20260907_0004`）；Supplier Delete & Import Patch MERGED / IMPLEMENTED（Revision `20260908_0005`）；Account / Registration / Profile IMPLEMENTED / VERIFIED（Revision `20260908_0006`）；Custom Role Create IMPLEMENTED（Revision `20260908_0007`）；Post-Merge P1 Transaction / Validation Hardening VERIFIED（无 Migration）；Product Master 与 Product Import IMPLEMENTED（Revision `20260909_0008` → `20260910_0015`）。当前 Alembic 迁移链为单 Head：`20260907_0004` → `20260908_0005` → `20260908_0006` → `20260908_0007` → `20260909_0008` → `20260909_0009` → `20260910_0010`（用户逻辑删除）→ `20260910_0013` → `20260910_0014` → `20260910_0015`。分支与合入状态以 GitHub / `main` 历史为准。

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
- [x] 商品当前成本价承载当前供应商报价；一期不建设独立报价库
- [x] 商品大表是正式商品主数据来源
- [x] 大表一行 = 一条具体正式商品
- [x] 一期不强制 SPU/SKU
- [x] 真实供应商字段资料与 Supplier Field Dictionary 已冻结
- [x] 真实整理后商品大表字段边界已冻结
- [x] Product / Category / Pricing Schema Design Ready
- [x] Product Source Supplier Resolution Schema Decision Ready

## 下一步

- 主任务：Product Import 已实现固定 32 列 Staging、类目/价格直接保存、WPS/Excel 内嵌图片相对本地保存、来源供应商精确匹配、预览、人工解析和原子 Confirm（Revision `20260910_0015`，ADR-0010/0011）。
- 后续任务：准备真实商品大表需要的有效 Supplier Master，并处理 Excel 的空供应商；类目 Source Loader 不再是商品 Confirm 前置条件。
- 业务冻结：Supplier Product Quote 已取消；后续供应商新报价直接更新正式 Product 的 `cost_price`，并原子重算派生价格；不创建报价历史、有效期或比价模块。
- Auth 后续范围：Refresh Token、Session、Multi-device Logout 与 Role Delete / disable policy 仍待后续冻结；User Logical Delete 已实现，Profile 与顶部当前角色已显示数据库角色、权限中文名称。

## Blocker

- Repository：无代码合并 Blocker。
- Supplier：Delete & Import 已合入；未确认的企业、税务、地址、银行、资质等字段仍不得自行添加。资质业务字段及其 API 继续冻结。
- Product / Catalog：Product Master 与 Product Import 已实现；实际 Confirm 仅受空/无效来源供应商阻塞，Product 删除策略和无受控类目关联 Product 的独立成本价维护仍待后续范围。

## Workstreams / Implementation Context

- Auth Real API Integration：已完成真实 Auth API 联调；分支与合入状态以 GitHub / `main` 历史为准。
- Business Sequence：`sys_biz_sequence` Migration、并发安全取号服务与 MySQL 并发测试已完成；分支与合入状态以 GitHub / `main` 历史为准。
- Supplier：Backend MERGED / Frontend REAL_API_IMPLEMENTED；Delete & Import Patch MERGED / IMPLEMENTED（Revision `20260908_0005`），新增逻辑删除、`supplier:delete`、Excel 模板/校验预览/确认导入和 Web Admin 控制。
- Auth/RBAC：Auth Sprint 1 当前范围 IMPLEMENTED / VERIFIED（Revision `20260908_0006`），包括注册审批、用户角色/角色权限管理、动态权限目录、Profile 与修改密码；Web Admin UI Optimization 分支已完成内部 UUID 隐藏、中文用户状态、角色名称展示（只读 `role_names` 响应字段）、待审批数字角标与审批历史列表的前后端本地验证；角色只可分配给 `ENABLED` 用户，浏览器验收待完成；Refresh Token、Session、Multi-device Logout 仍属未来范围。
- Role Management：自定义角色创建 IMPLEMENTED（Revision `20260908_0007`）。新增 `system:role:create`，角色编码不可修改且符合小写英文/数字/下划线规范，角色初始无权限；系统管理员内置角色存在时由迁移自动获得创建权限。角色编辑、停用与删除仍属未来范围。
- Post-Merge Hardening：Request transaction ownership、Service caller-owned transaction participation、Account association ID 幂等去重与 Supplier UUID Router validation 已验证；ADR-0007 冻结事务规则，无 Migration 变化。
- Catalog：`IMPLEMENTED / PRODUCT_IMPORT_DIRECT_VALUE_MODE`；固定商品大表直接保存三级类目文字和价格值，`source_supplier_id` 仍是正式关系；Product 列表、详情、导入预览、供应商人工解析和原子 Confirm 已可用，真实类目源数据无需作为 Confirm 前置条件。
- Product Cost Pricing：`cost_price` 是当前成本价和当前供应商报价，不建设 `scm_supplier_product_quote`；成本价更新已受 `product:cost:update` 保护，并原子重算已冻结派生值。
