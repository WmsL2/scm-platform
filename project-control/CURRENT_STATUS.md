# 当前项目状态 / Current Project Status

项目：众诚智链商品管理平台
Repository：zhongcheng-scm-platform
Baseline：Sprint 1 Auth Kernel / Web Admin Auth Real API Integration merged; Supplier Delete & Import and Account / Registration / Profile verified; post-merge P1 hardening verified
日期：2026-09-11

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
进度：Auth Kernel DONE；Web Admin Auth DONE / REAL API VERIFIED；Business Sequence DONE / IMPLEMENTED（Revision `20260907_0003`）；Supplier Master Backend DONE / MERGED via PR #13（Revision `20260907_0004`）；Supplier Delete & Import Patch MERGED / IMPLEMENTED（Revision `20260908_0005`）；Supplier Name Uniqueness / Deleted-Record Recovery IMPLEMENTED（Revision `20260910_0016`）；Account / Registration / Profile IMPLEMENTED / VERIFIED（Revision `20260908_0006`）；Custom Role Create / Safe Delete IMPLEMENTED（Revision `20260908_0007`、`20260911_0018`）；Auth Session Refresh IMPLEMENTED（Revision `20260911_0021`）；Post-Merge P1 Transaction / Validation Hardening VERIFIED（无 Migration）；Product Master、Import、防重、基础资料编辑、停用/启用、永久删除、通过行分批导入、模板下载及供应商合作状态联动 IMPLEMENTED（Revision `20260909_0008` → `20260911_0022`）。当前 Alembic 迁移链为单 Head：`20260907_0004` → `20260908_0005` → `20260908_0006` → `20260908_0007` → `20260909_0008` → `20260909_0009` → `20260910_0010`（用户逻辑删除）→ `20260910_0013` → `20260910_0014` → `20260910_0015` → `20260910_0016`（供应商名称唯一）→ `20260910_0017`（合作状态恢复）→ `20260911_0018`（商品防重、编辑与角色删除权限）→ `20260911_0019`（商品逻辑删除）→ `20260911_0020`（商品停用与永久删除）→ `20260911_0021`（Auth 服务端会话刷新）→ `20260911_0022`（通过行分批导入）。分支与合入状态以 GitHub / `main` 历史为准。

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

- 主任务：Product Import 已实现固定 32 列 Staging、批准模板下载、类目/价格直接保存、WPS/Excel 内嵌图片相对本地保存、来源供应商精确匹配、通过/不通过预览筛选、人工解析、供应商 + SKU 防重和通过行原子 Confirm；同键停用商品阻止导入，永久删除后可按新 Excel 新建（Revision `20260911_0022`，ADR-0010/0011/0015/0016）。
- 后续任务：准备真实商品大表需要的有效 Supplier Master，并处理 Excel 的空供应商；类目 Source Loader 不再是商品 Confirm 前置条件。
- 业务冻结：Supplier Product Quote 已取消；后续供应商新报价直接更新正式 Product 的 `cost_price`，并原子重算派生价格；不创建报价历史、有效期或比价模块。
- Auth 会话：Refresh Token、服务端 Session、令牌轮换、三天无活动过期、三十天绝对过期和全设备失效已实现；管理员设备会话管理页与 Role disable policy 仍待后续冻结。

## Blocker

- Repository：无代码合并 Blocker。
- Supplier：名称唯一与重复数据清理已实现：同名只保留最早历史记录，后建重复记录已物理删除；创建/导入遇到已逻辑删除的同名记录会恢复并覆盖。合作状态已冻结为 NORMAL ↔ STOPPED / BLACKLIST，恢复均保留原因和历史；Import Confirm 已按原子持久化加固：锁定实际导入行、flush 成功和数量一致后才确认批次，异常整批回滚。未确认的企业、税务、地址、银行、资质等字段仍不得自行添加。资质业务字段及其 API 继续冻结。
- Product / Catalog：Product Master 与 Product Import 已实现；实际 Confirm 仅写入当前通过行，空/无效来源供应商或同键正常/停用商品等失败行保留在 Staging，不会入库。Product 已冻结为 `ACTIVE` / `DISABLED`：停用保留业务键并阻止导入；仅已停用商品可由 `product:purge` 永久删除，删除后可新建同键商品。覆盖式 Excel 更新和无受控类目关联 Product 的独立成本价维护仍待后续范围。

## Workstreams / Implementation Context

- Auth Real API Integration：已完成真实 Auth API 联调；分支与合入状态以 GitHub / `main` 历史为准。
- Business Sequence：`sys_biz_sequence` Migration、并发安全取号服务与 MySQL 并发测试已完成；分支与合入状态以 GitHub / `main` 历史为准。
- Supplier：Backend MERGED / Frontend REAL_API_IMPLEMENTED；Delete & Import Patch MERGED / IMPLEMENTED（Revision `20260908_0005`），新增逻辑删除、`supplier:delete`、Excel 模板/校验预览和 Web Admin 控制。Name Uniqueness Patch IMPLEMENTED（Revision `20260910_0016`）：活动同名创建/编辑受阻，逻辑删除同名记录可恢复覆盖；Excel 活动重名/表内重名按行提示。ADR-0012 已冻结归档状态选择：新建、编辑和 Excel Confirm 可选择 `DRAFT` / `PENDING` / `ARCHIVED`；Excel 保持预览后由上传者显式确认，合作状态固定为 `NORMAL`。Import Confirm Integrity Fix IMPLEMENTED：确认时直接锁定批次行、flush 并核验实际处理数后才置为成功；历史异常确认批次不自动重放。
- Auth/RBAC：Auth Sprint 1 与 Session Refresh IMPLEMENTED / VERIFIED（Revision `20260908_0006`、`20260911_0021`），包括注册审批、用户角色/角色权限管理、动态权限目录、Profile、修改密码、短期 Access Token、旋转 HttpOnly Refresh Token、服务端可撤销会话及前端 401 单次自动恢复；角色只可分配给 `ENABLED` 用户，浏览器手工验收待完成。
- Role Management：自定义角色创建 IMPLEMENTED（Revision `20260908_0007`）；安全删除 IMPLEMENTED（Revision `20260911_0018`）。仅未分配给有效用户的自定义角色可逻辑删除；内置角色、仍关联有效用户的角色一律拒绝删除。权限配置页按权限码前缀动态分组，支持模块折叠、模块全选/半选和单项勾选。角色编辑与停用仍属未来范围。
- Post-Merge Hardening：Request transaction ownership、Service caller-owned transaction participation、Account association ID 幂等去重与 Supplier UUID Router validation 已验证；ADR-0007 冻结事务规则，无 Migration 变化。
- Catalog：`IMPLEMENTED / PRODUCT_IMPORT_PARTIAL_CONFIRM`；固定商品大表直接保存三级类目文字和价格值，`source_supplier_id` 是正式关系；来源供应商 + SKU 为 Product 防重业务键。Product 列表、详情、受控基础资料编辑、停用/启用、受确认的永久删除、模板下载、导入预览、通过/不通过筛选、供应商人工解析和通过行原子 Confirm 已可用；失败行不入库，已导入行不能重复 Confirm；同键正常或停用商品均阻止，不恢复也不覆盖。真实类目源数据无需作为 Confirm 前置条件。Supplier Detail Related Products IMPLEMENTED：`product:list` 可按来源供应商精确筛选正式商品；供应商停用/拉黑时关联商品不可查询或维护，恢复合作后自动恢复可见。
- Product Cost Pricing：`cost_price` 是当前成本价和当前供应商报价，不建设 `scm_supplier_product_quote`；成本价更新已受 `product:cost:update` 保护，并原子重算已冻结派生值。
- Web Admin Data Refresh：统一 API 客户端已设置 `cache: no-store`；新增、编辑、删除和导入确认后的页面重新加载不会复用浏览器中的旧 GET 响应，前端测试、类型检查和生产构建已验证。
