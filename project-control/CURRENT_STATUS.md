# 当前项目状态 / Current Project Status

项目：众诚智链商品管理平台
Repository：zhongcheng-scm-platform
Baseline：Sprint 1 Auth Kernel / Web Admin Auth Real API Integration merged; Supplier Delete & Import and Account / Registration / Profile verified; post-merge P1 hardening verified
日期：2026-09-15

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
进度：Auth Kernel DONE；Web Admin Auth DONE / REAL API VERIFIED；Business Sequence DONE / IMPLEMENTED（Revision `20260907_0003`）；Supplier Master Backend DONE / MERGED via PR #13（Revision `20260907_0004`）；Supplier Delete & Import Patch MERGED / IMPLEMENTED（Revision `20260908_0005`）；Supplier Name Uniqueness / Deleted-Record Recovery IMPLEMENTED（Revision `20260910_0016`）；Account / Registration / Profile IMPLEMENTED / VERIFIED（Revision `20260908_0006`）；Custom Role Create / Safe Delete IMPLEMENTED（Revision `20260908_0007`、`20260911_0018`）；Auth Session Refresh IMPLEMENTED（Revision `20260911_0021`）；Post-Merge P1 Transaction / Validation Hardening VERIFIED（无 Migration）；Product Master、Import、防重、基础资料编辑、停用/启用、永久删除、通过行分批导入、模板下载、确认时图片落盘及供应商合作状态联动 IMPLEMENTED（Revision `20260909_0008` → `20260914_0023`）。当前 Alembic 迁移链为单 Head：`20260907_0004` → `20260908_0005` → `20260908_0006` → `20260908_0007` → `20260909_0008` → `20260909_0009` → `20260910_0010`（用户逻辑删除）→ `20260910_0013` → `20260910_0014` → `20260910_0015` → `20260910_0016`（供应商名称唯一）→ `20260910_0017`（合作状态恢复）→ `20260911_0018`（商品防重、编辑与角色删除权限）→ `20260911_0019`（商品逻辑删除）→ `20260911_0020`（商品停用与永久删除）→ `20260911_0021`（Auth 服务端会话刷新）→ `20260911_0022`（通过行分批导入）→ `20260914_0023`（确认时图片落盘与过期临时媒体清理）。分支与合入状态以 GitHub / `main` 历史为准。

投标项目核心已在分支 `feat/bid-project-core` 实现：新增唯一 Migration `20260915_0024`，包含项目、模板、文件版本、需求行、事件、匹配和人工选品共享表，项目编号序列及投标权限。项目创建、ORIGINAL 保存、模板指纹识别、分页查询、文件下载、报价版本、提交和结果接口已完成；真实买家 Excel 尚未提供，因此当前不预置客户模板或报价列。2 号匹配和 3 号前端可在本结构上并行开发。

投标项目已增加业务开始时间 `start_at`（Revision `20260916_0025`），与用户填写的 `deadline_at` 和系统审计 `created_at` 明确分离；历史记录允许为空。

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

- 主任务：Product Import 已实现固定 32 列 Staging、批准模板下载、有效商城三级类目绑定、WPS/Excel 图片仅在实际 Confirm 行相对本地保存、来源供应商精确匹配、通过/更新/不通过预览筛选、人工解析、供应商 + SKU 正常同键更新以及新增/更新原子 Confirm；更新行显示变更字段并保留原商品 ID、创建审计与状态，停用同键商品仍阻止入库。过期未完成任务仅清理自身临时源文件/未导入行媒体，绝不清理正式 Product 图片（Revision `20260917_0028`，合并 Head `20260917_0029`，ADR-0010/0011/0015/0016/0017/0018/0020）。
- 后续任务：准备真实商品大表需要的有效 Supplier Master，并处理 Excel 的空供应商；类目 Source Loader 不再是商品 Confirm 前置条件。
- 业务冻结：Supplier Product Quote 已取消；后续供应商新报价直接更新正式 Product 的 `cost_price`，并原子重算派生价格；不创建报价历史、有效期或比价模块。
- Auth 会话：Refresh Token、服务端 Session、令牌轮换、三天无活动过期、三十天绝对过期和全设备失效已实现；管理员设备会话管理页与 Role disable policy 仍待后续冻结。

## Blocker

- Repository：无代码合并 Blocker。
- Supplier：名称唯一与重复数据清理已实现：同名只保留最早历史记录，后建重复记录已物理删除；创建/导入遇到已逻辑删除的同名记录会恢复并覆盖。合作状态已冻结为 NORMAL ↔ STOPPED / BLACKLIST，恢复均保留原因和历史；Import Confirm 已按原子持久化加固：锁定实际导入行、flush 成功和数量一致后才确认批次，异常整批回滚。未确认的企业、税务、地址、银行、资质等字段仍不得自行添加。资质业务字段及其 API 继续冻结。
- Product / Catalog：Product Master 与 Product Import 已实现；实际 Confirm 写入当前通过新增行与正常同键更新行，空/无效来源供应商、同 Excel 重复或停用同键商品等失败行保留在 Staging，不会入库。Product 已冻结为 `ACTIVE` / `DISABLED`：停用保留业务键并阻止导入；仅已停用商品可由 `product:purge` 永久删除，删除后可新建同键商品。无受控类目关联 Product 的独立成本价维护仍待后续范围。

## Workstreams / Implementation Context

- Auth Real API Integration：已完成真实 Auth API 联调；分支与合入状态以 GitHub / `main` 历史为准。
- Business Sequence：`sys_biz_sequence` Migration、并发安全取号服务与 MySQL 并发测试已完成；分支与合入状态以 GitHub / `main` 历史为准。
- Supplier：Backend MERGED / Frontend REAL_API_IMPLEMENTED；Delete & Import Patch MERGED / IMPLEMENTED（Revision `20260908_0005`），新增逻辑删除、`supplier:delete`、Excel 模板/校验预览和 Web Admin 控制。Name Uniqueness Patch IMPLEMENTED（Revision `20260910_0016`）：活动同名创建/编辑受阻，逻辑删除同名记录可恢复覆盖；Excel 活动重名/表内重名按行提示。ADR-0012 已冻结归档状态选择：新建、编辑和 Excel Confirm 可选择 `DRAFT` / `PENDING` / `ARCHIVED`；Excel 保持预览后由上传者显式确认，合作状态固定为 `NORMAL`。Import Confirm Integrity Fix IMPLEMENTED：确认时直接锁定批次行、flush 并核验实际处理数后才置为成功；历史异常确认批次不自动重放。
- Auth/RBAC：Auth Sprint 1 与 Session Refresh IMPLEMENTED / VERIFIED（Revision `20260908_0006`、`20260911_0021`），包括注册审批、用户角色/角色权限管理、动态权限目录、Profile、修改密码、短期 Access Token、旋转 HttpOnly Refresh Token、服务端可撤销会话及前端 401 单次自动恢复；角色只可分配给 `ENABLED` 用户，浏览器手工验收待完成。
- Auth Entry UI：登录与注册已合并为同一认证卡片，通过左右页签原地切换；真实接口、
  注册审批、`/login` 与 `/register` 兼容入口保持不变。
- Role Management：自定义角色创建 IMPLEMENTED（Revision `20260908_0007`）；安全删除 IMPLEMENTED（Revision `20260911_0018`）。仅未分配给有效用户的自定义角色可逻辑删除；内置角色、仍关联有效用户的角色一律拒绝删除。权限配置页按权限码前缀动态分组，支持模块折叠、模块全选/半选和单项勾选。角色编辑与停用仍属未来范围。
- Post-Merge Hardening：Request transaction ownership、Service caller-owned transaction participation、Account association ID 幂等去重与 Supplier UUID Router validation 已验证；ADR-0007 冻结事务规则，无 Migration 变化。
- Catalog：`IMPLEMENTED / PRODUCT_IMPORT_PARTIAL_CONFIRM`；固定商品大表以一级、二级、三级文本唯一匹配有效商城 Category，正式 Product 写入 `category_id` 与 Category-owned 路径，价格值仍直接保存；`source_supplier_id` 是正式关系，来源供应商 + SKU 为 Product 防重业务键。历史 Product 回填必须在目标库存在候选记录时重新预检；当前配置开发库的 `scm_product` 为 0 条，未执行历史更新。Product 列表、详情、受控基础资料编辑、停用/启用、受确认的永久删除、模板下载、导入预览、通过/不通过筛选、供应商人工解析和通过行原子 Confirm 已可用；`DISPIMG` 预览显示确认后保存，临时源文件写入后会显式异步加载关联数据，避免延迟加载导致预览 500，只有正式通过行才生成图片文件。失败行不入库，已导入行不能重复 Confirm；同键正常或停用商品均阻止，不恢复也不覆盖。Supplier Detail Related Products IMPLEMENTED：`product:list` 可按来源供应商精确筛选正式商品；供应商停用/拉黑时关联商品不可查询或维护，恢复合作后自动恢复可见。
- Product Cost Pricing：`cost_price` 是当前成本价和当前供应商报价，不建设 `scm_supplier_product_quote`；成本价更新已受 `product:cost:update` 保护，并原子重算已冻结派生值。
<<<<<<< HEAD
- Bid Matching / Task 2-3：PR #46 已提供投标共享 Schema 后，匹配任务、候选持久化、Top 20 可解释候选、人工选品不可变快照、无报价与四个受权限保护的 API 已完成。Task 3 已实现 Web 项目列表、创建、详情、文件版本和服务端分页匹配工作台；候选按需加载且历史展示不可变快照。项目业务开始时间 `start_at` 与审计 `created_at` 已分离。基础信息可由 `bid:update` 在允许状态编辑；删除采用 `bid:void` 业务作废，`VOIDED` 为历史保留终态（Revisions `20260916_0025`、`20260916_0026`、`20260916_0027`）。真实 API 浏览器验收仍等待已识别 BidTemplate，Template Management 仍为后续任务。
=======
- Product Operator Display：商品主数据已增加“操作记录”页签，复用正式 Product 列表和分页，显示既有 `created_by` / `created_at` / `updated_by` / `updated_at` 所表达的导入人、导入时间、最后更新人和最后更新时间；接口批量解析历史用户名，不新增表或 Migration。
- Bid Matching / Task 2：PR #46 已提供投标共享 Schema 后，2 号任务已接入匹配任务、候选持久化、Top 20 可解释候选、人工选品不可变快照、无报价与四个受权限保护的 API。MySQL 持久化测试、全量后端测试、Ruff 和 mypy 已通过；3 号前端联调及未来 ARQ Worker 验收尚未完成。
>>>>>>> origin/main
- Web Admin Data Refresh：统一 API 客户端已设置 `cache: no-store`；新增、编辑、删除和导入确认后的页面重新加载不会复用浏览器中的旧 GET 响应，前端测试、类型检查和生产构建已验证。
- Category Management：基于既有 `scm_category` 三级维表补齐列表、详情、新增、编辑、Product 引用保护删除、启用选择和 Excel 导入；未新增 Schema/Migration/专属权限，复用 Catalog 既有权限。
