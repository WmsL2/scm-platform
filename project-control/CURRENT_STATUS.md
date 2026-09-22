# 当前项目状态 / Current Project Status

项目：众诚智链商品管理平台
Repository：zhongcheng-scm-platform
Baseline：Sprint 1 Auth Kernel / Web Admin Auth Real API Integration merged; Supplier Delete & Import and Account / Registration / Profile verified; post-merge P1 hardening verified
日期：2026-09-22

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

商品主数据 2026 模板、组合筛选、Product Master 直接类目候选及商品与类目维表脱钩已在分支 `feat/product-master-category-filter-options` 实现；最新单 Head 为 `20260918_0032`（基于 `20260918_0031`）。

商品导入数值安全、4,000+ 行分页与并发确认保护已在分支 `feat/product-import-safety-concurrency` 实现；Revision `20260918_0033` 为暂存行增加标准化值和 Product 版本快照，Revision `20260918_0034` 将六个正式价格字段扩展为 `DECIMAL(65,30)` 以无损保存 Excel 价格原值。Confirm 以供应商 + SKU 锁及版本冲突返回 409，重型工作簿操作默认每 API 进程并发 1。内嵌图片改为 Confirm 时逐张流式解码与保存，移除旧 50MB 累计截断；TIFF/EMF 等转 PNG，公式缺图或坏图按行阻止确认，单图默认上限 64MB（ADR-0029，无 Migration）。历史商品图片不自动回填，重新导入后生效。

商品导入锁竞争控制已在分支 `fix/product-import-lock-contention` 实现：Revision `20260922_0038` 添加 Import Task 的 `status + created_at` 清理索引；机会性过期清理按状态限批并用 `FOR UPDATE SKIP LOCKED` 跳过被占用旧任务。Confirm 先准备内嵌图片，再锁定 Task 并重新校验后写入，避免图片处理期间长期持有 Task 锁；临时源 Excel 的成功后删除、Discard 和 24 小时过期清理规则不变（ADR-0034）。

商品导入临时源 Excel 24 小时保留已在分支 `feat/product-import-confirm-reupload` 实现：含 `DISPIMG` 的预览暂存源文件，Confirm 成功后立即删除；关闭预览弹窗调用 discard 接口作废任务并立即删除。浏览器异常关闭、断网或进程中断时，未完成任务在后续导入操作中按 24 小时边界过期清理；无内嵌图片任务不保存源文件（ADR-0031，无 Migration）。

商品导入预览已支持导出全部未处理的不通过行：导出文件直接复用商品主数据下载的正式模板及其样式，从第 2 行写入失败原值，第二工作表提供原 Excel 行号与错误原因，运营修正后可直接重新上传。失败行中的公式按新行号平移；若临时源工作簿仍可用，仅携带失败行引用的 `DISPIMG` 内嵌图片，避免复制整本大表的无关媒体（无 Migration，复用 `product:import`）。

商品自选字段 Excel 导出的前端等待上限调整为 5 分钟（原 60 秒）；后端仍同步生成文件，导入请求的超时配置不变。此次仅为上线阶段减少浏览器过早取消导出，不属于导出性能优化。
商品导出成功后会显示提示；导出表头按所选字段匹配正式下载模板的颜色、字体、边框、对齐与行高，原有导出顺序和图片嵌入方式保持不变（无 Migration、无新权限）。
商品导出数据区现为每个单元格绘制细边框，包含空值与图片。5000 行 × 43 列模拟基准中，工作簿生成约由 0.14 秒增至 1.04 秒，压缩文件约由 49 KB 增至 479 KB；这不包含数据库查询和图片读取，非正式服务器性能结论。

现有 Excel 导入／导出及投标文件下载入口已增加前端请求耗时显示（X分X秒），运行时实时更新、结束后保留成功或失败耗时；商品、供应商、类目的模板下载不计时。四个 Excel 导入入口的全屏遮罩也同步显示已耗时。该指标不代表纯后端处理时间，不新增数据库字段、API 或权限。

真实 4,000+ 行 Confirm 的浏览器等待时间已设为 15 分钟；正式 Product 的供应商 + SKU 查询和锁定按稳定顺序每 500 组分批，避免 MySQL 默认 `range_optimizer_max_mem_size=8MB` 对超大复合 `IN` 查询的警告，仍保持单次 Confirm 的事务原子性和并发保护（无 Migration）。

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

- 主任务：Product Master 已升级为固定 43 列模板；仅 SKU 与合格供应商必填，其余 41 列（含三级类目）可为空并保存为 `NULL`。覆盖式同键重新导入、成功提交后的旧图片回收、组合筛选、可搜索类目联动、自定义列表列和全字段详情/编辑均已实现。`scm_product` 与导入暂存行不依赖 `category_id`，类目维表保留为独立管理模块（ADR-0033）。商品导入已改为分块上传与磁盘只读解析，默认支持 1GB / 100,000 行，浏览器预览超时为 15 分钟（无 Alembic Revision，ADR-0022）。供应商 + SKU 仍为不可修改业务键，停用同键商品仍阻止入库。
- 后续任务：准备真实商品大表需要的有效 Supplier Master，并处理 Excel 的空供应商；供应商手工新增与 Excel 导入均仅要求供应商名称，其余已冻结字段可后补；类目 Source Loader 不再是商品 Confirm 前置条件。
- 业务冻结：Supplier Product Quote 已取消；正式 `cost_price` 允许为空，43 列 Excel 的不可解析数值写为 NULL；后续供应商新报价的专用成本价接口仍要求大于零且不自动重算其他价格；不创建报价历史、有效期或比价模块（ADR-0024、ADR-0030）。
- Auth 会话：Refresh Token、服务端 Session、令牌轮换、三天无活动过期、三十天绝对过期和全设备失效已实现；管理员设备会话管理页与 Role disable policy 仍待后续冻结。
- 部署初始化：通过 `INITIAL_ADMIN_USERNAME` / `INITIAL_ADMIN_PASSWORD` 可一次性创建全权限 `boss` 管理员；同名账号一旦存在（包括逻辑删除）不被自动重建，创建后可安全移除环境变量并按常规账号管理删除该账号（ADR-0023，无 Migration）。

## Blocker

- Repository：无代码合并 Blocker。
- Supplier：手工新增与 Excel 导入均仅要求供应商名称，主营品牌、主要优势和联系人资料可留空后补；名称唯一与重复数据清理已实现，同名只保留最早历史记录，后建重复记录已物理删除，创建/导入遇到已逻辑删除的同名记录会恢复并覆盖。合作状态已冻结为 NORMAL ↔ STOPPED / BLACKLIST，恢复均保留原因和历史；Import Confirm 已按原子持久化加固：锁定实际导入行、flush 成功和数量一致后才确认批次，异常整批回滚。未确认的企业、税务、地址、银行、资质等字段仍不得自行添加。资质业务字段及其 API 继续冻结。
- Product / Catalog：Product Master 与 Product Import 已实现；实际 Confirm 写入当前通过新增行与正常同键更新行。仅 SKU 或来源供应商为空/无效、同 Excel 重复、停用同键商品以及公式图片缺失/不可解码等失败行保留在 Staging；三级类目为空允许入库。Product 已冻结为 `ACTIVE` / `DISABLED`：停用保留业务键并阻止导入；仅已停用商品可由 `product:purge` 永久删除，删除后可新建同键商品。Product 已不再关联 Category Master。
- Product Import 空供应商预览已加固：当整份 Excel 没有任何有效供应商名称时，后端显式使用空匹配集合，不在 `flush` 后触发 AsyncSession 懒加载；预览正常返回并将相关行标记为“供应商不能为空”。
- Excel 导入上线防误操作已实现第一版并覆盖全部 4 个入口：商品上传预览与 Confirm、供应商上传预览与 Confirm、类目原子导入、投标项目 Excel 创建。处理期间以前端全屏遮罩锁定交互，阻止站内路由切换，并对刷新或关闭页面请求浏览器原生确认；成功、失败或超时后自动解锁。该实现是紧急上线用的页面级保护，导入仍依赖当前页面请求，长期后台异步任务化尚未实施。

## Workstreams / Implementation Context

- Auth Real API Integration：已完成真实 Auth API 联调；分支与合入状态以 GitHub / `main` 历史为准。
- Business Sequence：`sys_biz_sequence` Migration、并发安全取号服务与 MySQL 并发测试已完成；分支与合入状态以 GitHub / `main` 历史为准。
- Supplier：Backend MERGED / Frontend REAL_API_IMPLEMENTED；Delete & Import Patch MERGED / IMPLEMENTED（Revision `20260908_0005`），新增逻辑删除、`supplier:delete`、Excel 模板/校验预览和 Web Admin 控制。Name Uniqueness Patch IMPLEMENTED（Revision `20260910_0016`）：活动同名创建/编辑受阻，逻辑删除同名记录可恢复覆盖；Excel 活动重名/表内重名按行提示。ADR-0012 已冻结归档状态选择：新建、编辑和 Excel Confirm 可选择 `DRAFT` / `PENDING` / `ARCHIVED`；Excel 保持预览后由上传者显式确认，合作状态固定为 `NORMAL`。Import Confirm Integrity Fix IMPLEMENTED：确认时直接锁定批次行、flush 并核验实际处理数后才置为成功；历史异常确认批次不自动重放。
- Auth/RBAC：Auth Sprint 1 与 Session Refresh IMPLEMENTED / VERIFIED（Revision `20260908_0006`、`20260911_0021`），包括注册审批、用户角色/角色权限管理、动态权限目录、Profile、修改密码、短期 Access Token、旋转 HttpOnly Refresh Token、服务端可撤销会话及前端 401 单次自动恢复；角色只可分配给 `ENABLED` 用户，浏览器手工验收待完成。
- Auth Entry UI：登录与注册已合并为同一认证卡片，通过左右页签原地切换；真实接口、
  注册审批、`/login` 与 `/register` 兼容入口保持不变。
- Role Management：自定义角色创建 IMPLEMENTED（Revision `20260908_0007`）；安全删除 IMPLEMENTED（Revision `20260911_0018`）。仅未分配给有效用户的自定义角色可逻辑删除；内置角色、仍关联有效用户的角色一律拒绝删除。权限配置页按权限码前缀动态分组，支持模块折叠、模块全选/半选和单项勾选。角色编辑与停用仍属未来范围。
- Post-Merge Hardening：Request transaction ownership、Service caller-owned transaction participation、Account association ID 幂等去重与 Supplier UUID Router validation 已验证；ADR-0007 冻结事务规则，无 Migration 变化。
- Catalog：`IMPLEMENTED / PRODUCT_MASTER_CATEGORY_DECOUPLED`；固定商品大表仅要求 SKU 与供应商，三级类目及其他 41 列可为空，且不匹配或写入 Category ID，Excel 价格直接保存。正常同键商品可覆盖更新，停用同键商品仍阻止；空 Excel 单元格清空旧值。Product 列表提供综合搜索、类目筛选、京东价／利润等闭区间筛选，以及所属公司、采销员、品牌、供应商的远程搜索多选筛选；同字段多选按 OR，其他条件按 AND。商品图片、SKU、商品名称固定在前三列，其余完整业务列按勾选顺序本地保存和显示；详情/编辑覆盖全部业务字段，供应商与 SKU 只读，图片仅通过受控上传/清除维护。
- Product Price Maintenance：`cost_price` 是当前成本价和当前供应商报价，不建设 `scm_supplier_product_quote`；正式成本价可为空，导入数值无效时保存 NULL。`product:cost:update` 仍只接受有效正数并仅保存成本价，所有价格、利润和比例独立维护（ADR-0024、ADR-0030）。
- Product Operator Display：商品主数据已增加“操作记录”页签，复用正式 Product 列表和分页，显示既有 `created_by` / `created_at` / `updated_by` / `updated_at` 所表达的导入人、导入时间、最后更新人和最后更新时间；接口批量解析历史用户名，不新增表或 Migration。
- Bid Matching / Task 2-3：PR #46 已提供投标共享 Schema 后，匹配任务、候选持久化、Top 20 可解释候选、人工选品不可变快照、无报价与四个受权限保护的 API 已完成。Task 3 已实现 Web 项目列表、创建、详情、文件版本和服务端分页匹配工作台；候选按需加载且历史展示不可变快照。项目业务开始时间 `start_at` 与审计 `created_at` 已分离。基础信息可由 `bid:update` 在允许状态编辑；删除采用 `bid:void` 业务作废，`VOIDED` 为历史保留终态（Revisions `20260916_0025`、`20260916_0026`、`20260916_0027`）。真实 API 浏览器验收仍等待已识别 BidTemplate，Template Management 仍为后续任务。
- Web Admin Data Refresh：统一 API 客户端已设置 `cache: no-store`；新增、编辑、删除和导入确认后的页面重新加载不会复用浏览器中的旧 GET 响应，前端测试、类型检查和生产构建已验证。
- Web Admin LAN HTTP：统一 HTTP 客户端的请求 ID 在普通 HTTP 局域网 IP 的非安全浏览器上下文中可回退生成，避免 `crypto.randomUUID()` 不可用而在 `fetch` 前中断登录等 API 调用；该回退不用于认证或安全令牌。
- Category Management：基于既有 `scm_category` 三级维表补齐列表、详情、新增、编辑、删除、启用选择和 Excel 导入；商品不再引用该表，删除不再因 Product 被阻止。
