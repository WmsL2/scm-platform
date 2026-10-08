# 当前项目状态 / Current Project Status

项目：众诚智链商品管理平台
Repository：zhongcheng-scm-platform
Baseline：Sprint 1 Auth Kernel / Web Admin Auth Real API Integration merged; Supplier Delete & Import and Account / Registration / Profile verified; post-merge P1 hardening verified
日期：2026-10-08

> 2026-10-08：类型 5 已新增可审计的方案选择持久化。方案选择与方案内商品确认在同一事务
> 完成，刷新、重新进入及完成选品后仍显示绿色高亮和“已选方案”；允许累计选择多张方案。
> Revision `20261008_0047`，新增选择 API，沿用 `recommendation:review`，推荐模块 68 项测试、
> Ruff、Mypy、前端类型检查、类型 5 工作台测试和生产构建已通过（ADR-0049）。

> 2026-10-08：类型 5 方案编排已改为每个方案独立调用 DeepSeek，模型仅返回本次调用的
> `P0001` 短引用，后端映射到冻结 Candidate ID 并严格校验；结构或合同错误只重试当前方案。
> 修复 `ppt-v8` 确认阶段误用原始类目文字二次筛选导致批量确认 409。无 Migration、API、UI
> 或权限变化；推荐模块 65 项测试、Ruff、Mypy 已通过，真实 DeepSeek 与浏览器验收待执行。

> 2026-10-08：类型 5 不再因 DeepSeek 返回的有效商品数少于配置目标而丢弃整个方案。
> 配置数量现作为 AI 编排目标：少选方案正常持久化和展示，页面标注实际/目标数量；多选结果
> 截断到配置上限。未知引用、空方案和价格档外商品仍由后端拒绝。无 Migration、API 或权限变化；
> 推荐模块 67 项测试、Ruff、Mypy、前端类型检查、类型 5 工作台测试和生产构建已通过。

> 2026-10-08：类型 5 PPT 方案 AI 编排 Token 安全修复已在 `codex/fix/type5-token-safety` 实现，待审查。完整候选池不受截断；AI 使用基于预算的短 ID 轮换窗口，只输出有限核心商品，由后端从完整冻结价格档池补齐。价格档分别持久化，失败不会回滚既有方案；Revision `20261008_0048` 持久化每档生成状态，`20261008_0049` 冻结 Run 配置。已与 main PR #113 的方案选择持久化兼容：计划的选择者和时间可刷新读取，选择仍原子确认其冻结候选，重试不覆盖既有选择。`20261008_0050` 仅合并 `0047` 与 `0049` 的 Alembic 图。首次与重试按独立短 Session 编排，重试 API 只补齐当前 Run 缺失槽位。MySQL HTTP 专项验收已通过；真实 DeepSeek 与浏览器端到端验收待执行。

> 2026-09-30：类型 5 方案 AI 移除了“完整候选池超过 1,000 件即失败”的限制，改为按价格档独立传入该档冻结候选；当前每档技术传输保护为 5,000 件。新增价格档可用性接口，PPT 工作台显示按协议价计算的每档真实候选数、每方案要求数和准确不足原因。无 Migration、无权限变化；真实 DeepSeek 与浏览器验收待执行。

> 2026-09-30：类型 5 已独立实现与类型 4 同口径的 V8 受控召回：类型 5 自己维护需求解析、真实类目树冻结、类目 key 校验和完整候选快照，不能调用类型 4 选品 Service / Repository。随后类型 5 独立方案 AI 仅从已冻结候选 ID 组织价格档方案，后端严格校验。类型 4 的候选表和 Excel 导出不变。Revision `20260930_0046` 记录方案 AI 来源、模型和 Prompt 版本；推荐模块测试、Ruff、Mypy 已通过，真实 DeepSeek 和浏览器验收待执行。

> 2026-09-29：工作区标签拖拽已调整为浏览器式标签栏交互：完整标签预览的纵向位置固定在标签栏，横向坐标受标签栏左右边界约束；鼠标移出标签栏后仍可继续按横向位置换位，原标签位仅保留浅色虚线占位，避免拖到页面内容区出现孤立蓝框。无 Migration、API 或权限变化；前端类型检查、全量 Vitest（165 项）及生产构建已通过。

> 2026-09-29：自由推品 Requirement V8 已在 `codex/feat/recommendation-category-catalog-snapshot` 实现：需求解析仅保留客户明确类目原词，后端按正式可推荐商品、供应商状态及非类目硬条件生成并冻结一级、二级、三级类目树 JSON 快照，AI 只能返回其中存在的 key；选一级展开所有下级、选二级展开所有三级路径、选三级精确筛选。未知 key 被拒绝，明确类目无匹配不回退全库。Revision `20260929_0042` 新增 Run 快照 JSON 列。后端推荐核心/Agent/适配测试以及 Ruff、Mypy 已通过；前端类型检查、生产构建、真实 DeepSeek 新 Run 与浏览器验收待执行（ADR-0045）。

> 2026-09-30：类型 5 PPT 方案已在 `feat/type5-deepseek-python-ppt` 改为 DeepSeek + 本地 Python 渲染。类型 5 与类型 4 共用 DeepSeek 配置，但类型 5 的 DeepSeek 仅做需求理解和受控类目选择，不做商品排序；人工确认单品与套装后，`python-pptx` 按固定商品页生成原生可编辑 PPTX：顶部商品名称、左侧参数、中央分隔线、右侧商品图。正式商品的本地图片会自动插入，套装最多显示四张。类型 5 固定使用系统默认版式，不上传或读取客户 PPT 模板。移除 Kimi 运行依赖；无 Migration、权限变化。推荐模块 54 项测试、Ruff、Mypy、前端类型检查、类型 5 Vitest 与生产构建已通过；真实浏览器全流程视觉验收待执行（ADR-0046）。

> 2026-09-30：类型 5 使用独立的方案卡和具体商品详情，不重复展示类型 4 的全量候选表；每张方案可直接确认其中商品，手工组套仍在同页。无新增权限。

> 2026-09-30：类型 5 先冻结每个价格档内所有符合硬条件、类目选择及逐件协议价范围的正式商品，再从完整池为每档生成不同方案。每方案商品数量只规定单个方案的商品数，不限制检索池；方案可重叠但不完全相同，若商品池不足单方案数量则不生成不完整方案。价格档不计算方案总价。类型 4 逻辑未改变。Revision `20260930_0044`、`20260930_0045`；后端方案测试、Ruff、Mypy、前端 Type 5 Vitest、类型检查及生产构建已通过，真实 DeepSeek 新 Run 与浏览器验收待执行。

> 2026-09-28：修复商品详情编辑的百分比浮点精度问题。京东价毛利、扣点复核、毛利率、好评率、折扣率和价格虚高比例改用十进制字符串移位，数据库 `0.1970` 精确显示为 `19.70%` 并按 `0.1970` 回传，避免完整编辑请求因 JavaScript 浮点长尾触发 422。无 Migration、API 或权限变化。

> 2026-09-28：自由推品 Requirement V5 已在 `codex/feat/free-recommendation-brand-category` 实现：新 Run 保留 V4 数值硬条件全量召回，并且仅将客户以强制语气明确指定的品牌和类目作为筛选条件；Agent 为明确类目输出近义类目词以覆盖商品三级类目名称不完全一致的情形。场景、用途、数量、库存、物流和有效期仍忽略。无 Migration；后端 Ruff/Mypy/6 项推荐测试及前端类型检查/4 项工作台测试已通过，真实 DeepSeek 与浏览器验收待执行（ADR-0042）。

> 2026-09-28：自由推品推荐模板映射已在 `codex/feat/recommendation-template-column-mapping` 调整为列号 V2：重复表头可按第 N 列分别映射，商品字段允许重复选择并写入多个模板列；旧版唯一表头映射仍兼容读取和导出。无 Migration、无新增权限；推荐模块后端 56 项测试、Ruff/Mypy、前端类型检查、工作台 Vitest 与生产构建均通过（ADR-0043）。

> 2026-09-29：自由推品 Requirement V6 已在 `codex/feat/recommendation-template-column-mapping` 将“家电 250、厨具 135、日用 115”这类明确类目分配文本，以及“需要水杯、保温杯、随行杯”这类直接商品类目表达识别为类目硬筛选：仅类目名称进入语义匹配，所有符合硬条件及类目的商品都入池；数字不限制候选数量，也不是库存或下单数量。无 Migration、无新增权限；后端推荐模块 55 项测试、Ruff、Mypy 及前端类型检查、工作台 Vitest 6 项和生产构建均已通过（ADR-0044）；真实 DeepSeek 新 Run 与浏览器验收待执行。

> 2026-09-29：自由推品候选表已在 `codex/fix/recommendation-category-price-display` 对齐商品模块的列选择方式：图片、SKU、商品名称固定，三级类目、京东价、协议价及其他商品字段可按勾选显示且保存于当前浏览器；金额显示统一保留两位小数。无 Migration、无新增接口或权限；前端类型检查、10 项相关 Vitest 和生产构建均通过，真实浏览器验收待执行。

> 2026-09-28：类型4自由推品项目工作流第一版完成：项目状态按 `IMPORTED → MATCHING → SELECTING → READY → EXPORTED → SUBMITTED → WON / LOST` 推进，前三阶段由创建、Agent 执行与候选生成自动识别，后续由完成选品、导出、提交和人工登记结果推进。工作台改为 Agent 候选与人工选择左右双栏，支持增删、完成选品、返回调整、仅导出已选商品及中标/未中标登记；列表和详情统一状态颜色。无 Migration。

> 2026-09-28：自由推品 V4 已在 `codex/fix/free-recommendation-hard-constraints` 实现（无 Migration）：新 Run 仅按协议价、明确京东价、折扣率、点位等数值硬条件全量召回；不再按场景/类目/数量/价格有效期筛选、不再选 1–5 个类目、不再限 30 条或生成逐条理由。候选 API 改为分页，Web 支持本页全选与全部待确认候选的服务端范围确认；评分显示商品主数据 `positive_rating`。后端推荐测试、前端类型检查和相关 Vitest 已通过；真实浏览器和真实 DeepSeek 新 Run 验收仍待执行。

> 2026-09-24：自由推品 Requirement V3 已覆盖旧人工核验设计（无 Migration）。明确类目（含排除）以及协议价、明确京东价、折扣率、点位范围是确定性硬约束；点位复用 `gross_margin`。品牌、场景、履约物流和商品属性均为软参考；历史人工核验 JSON 不再阻止确认或导出。

> 2026-09-23：自由推品确认结果导出已在分支 `feat/free-recommendation-export` 实现，Migration `20260923_0040` 新增导出审计记录和人工 `factory_direct` 三态字段；复用 `recommendation:export`，导出保留上传模板格式并仅包含已确认候选。后端迁移和模块测试、前端类型检查/Vitest/生产构建已执行；真实浏览器导出验收仍需授权账号和实际确认 Run。

> 2026-09-24：自由推品确认编辑与导出闭环已加固：候选详情完整返回 Confirmation，确认更新不会清空未提交字段；全部人工确认字段可映射导出，空映射在确认时拒绝，导出清理连续模板数据区的旧映射数据。`EXPORTED` 后编辑确认回退到 `CONFIRMED`，无新增 Migration。

> 2026-09-23：自由推品 Recommendation A1–A4 底座已合入 `main`，Migration `20260923_0039`；B 的确定性 Run/候选/人工确认核心正在 `feat/free-recommendation-core` 实现，C 的 Agent/Web 和 A 的最终 Router 聚合尚未接入。导出仍等待“导出文件记录、厂家直供人工确认”最小数据合同评审。

> 2026-09-23：板块 C 已在 `feat/free-recommendation-agent-web` 实现 DeepSeek 适配器、受控 AgentRunner、任务执行入口和类型4 Web 工作台；真实商品检索、Run 持久化、确认和导出仍等待板块 B API 后统一对齐，DeepSeek 密钥由部署环境提供。

> 2026-09-23：`feat/free-recommendation-agent-web` 已合入最新 B 核心并完成第一轮 B/C 集成：Recommendation Router 注册至 API V1，Web 对齐 `/recommendation-projects`，Inline Agent 仅通过 B `RecommendationService` 完成需求保存、真实类目/商品检索和候选持久化。导出仍等待 Schema/Migration 决策。

> 2026-09-23：自由推品人工确认已修复 Run 串台：前端按当前 `run_id` 刷新并支持历史 Run 切换；候选可勾选后通过单事务批量确认（当前上限 500 条），重新生成不会覆盖原候选与确认结果。

> 2026-09-24：自由推品结果模板映射交互已按“上传模板列 → 商品主数据字段”调整：页面读取工作簿真实 Sheet/表头，左侧列名只读，右侧支持搜索 43 个商品主数据字段及人工“是否厂直”，同名自动匹配、重复表头阻止映射；后端既有映射存储和导出方向不变。投标项目筛选布局与模板文件名重复显示同步修复。无 Migration、无权限变化。

> 2026-09-24：修复自由推品导出 POST 返回后立即下载偶发 404：导出事务现在保证在响应发送前提交，避免下载 GET 先于附件及审计记录对其他数据库会话可见。

> 2026-09-24：Web Admin 顶部工作区标签基于 SortableJS 支持横向拖拽排序；采用 fallback 浮层避免原生拖放越界时出现禁止标志，并将路径顺序保存在当前浏览器。刷新、关闭后重新打开及重新登录后继续应用用户偏好。退出登录仍关闭业务标签，但不删除排序偏好。无 API、权限或 Migration 变化。

> 2026-09-24：企业工作台已从研发进度页调整为运营首页：Dashboard API 返回正式商品、正常合作供应商、进行中项目、待归档供应商及最近 5 个项目；待处理事项卡片暂显示 `--`。侧边栏仅在“供应商管理”显示有明确处理入口的待归档角标，商品与投标项目不显示待办角标。无新增表或 Migration。

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

商品导入锁竞争控制已实现：Revision `20260922_0038` 添加 Import Task 的 `status + created_at` 索引；Confirm 先准备内嵌图片，再锁定 Task 并重新校验后写入，避免图片处理期间长期持有 Task 锁。立即暂存清理策略（ADR-0035）移除了预览/Confirm 的机会性历史清理：全部 Confirm 成功或用户 Discard 后，临时源 Excel 和该批 Staging 数据立即删除；超过五小时的异常遗留由 ADR-0036 的独立命令处理。
商品导入超过五小时的异常遗留 Task 由独立命令清理（ADR-0036）：候选 Task ID 查询在独立只读事务结束后，逐条短锁并使用 `SKIP LOCKED` 和独立写事务实际提交删除；由服务器 Windows 计划任务每 15 分钟调用，不重新进入预览或 Confirm 请求路径。

商品导入临时源 Excel 24 小时保留已在分支 `feat/product-import-confirm-reupload` 实现：含 `DISPIMG` 的预览暂存源文件，Confirm 成功后立即删除；关闭预览弹窗调用 discard 接口作废任务并立即删除。浏览器异常关闭、断网或进程中断时，未完成任务在后续导入操作中按 24 小时边界过期清理；无内嵌图片任务不保存源文件（ADR-0031，无 Migration）。

商品导入预览已支持导出全部未处理的不通过行：导出文件直接复用商品主数据下载的正式模板及其样式，从第 2 行写入失败原值，第二工作表提供原 Excel 行号与错误原因，运营修正后可直接重新上传。失败行中的公式按新行号平移；若临时源工作簿仍可用，仅携带失败行引用的 `DISPIMG` 内嵌图片，避免复制整本大表的无关媒体（无 Migration，复用 `product:import`）。

商品自选字段 Excel 导出的前端等待上限调整为 5 分钟（原 60 秒）；后端仍同步生成文件，导入请求的超时配置不变。此次仅为上线阶段减少浏览器过早取消导出，不属于导出性能优化。
商品导出成功后会显示提示；导出表头按所选字段匹配正式下载模板的颜色、字体、边框、对齐与行高。商品图片现改为 WPS `DISPIMG` 公式和 `cellimages.xml` 内嵌媒体，不再生成 Excel Rich Data Place in Cell；导出顺序不变（无 Migration、无新权限）。
商品导出数据区现为每个单元格绘制细边框，包含空值与图片。5000 行 × 43 列模拟基准中，工作簿生成约由 0.14 秒增至 1.04 秒，压缩文件约由 49 KB 增至 479 KB；这不包含数据库查询和图片读取，非正式服务器性能结论。
商品自选字段导出文件的七个价格／金额列按四舍五入保留两位小数，Excel 单元格显示 `0.00`；百分比和其他字段不变，数据库价格原精度与正式导入模板不变。

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
- Supplier Master 主体名称判重第一版已在 `fix/supplier-name-normalized-dedup` 实现：新增、改名、Excel 预览及确认统一忽略中英文括号、空格与标点差异；原名和现有记录不自动合并。商品来源供应商匹配仍按 ADR-0008 严格规则。现阶段无数据库主体键唯一索引，极端并发写入变体仍需后续治理（ADR-0036）。
- Product / Catalog：Product Master 与 Product Import 已实现；实际 Confirm 写入当前通过新增行与正常同键更新行。仅 SKU 或来源供应商为空/无效、同 Excel 重复、停用同键商品以及公式图片缺失/不可解码等失败行保留在 Staging；三级类目为空允许入库。Product 已冻结为 `ACTIVE` / `DISABLED`：停用保留业务键并阻止导入；仅已停用商品可由 `product:purge` 永久删除，删除后可新建同键商品。Product 已不再关联 Category Master。
- Product Import 空供应商预览已加固：当整份 Excel 没有任何有效供应商名称时，后端显式使用空匹配集合，不在 `flush` 后触发 AsyncSession 懒加载；预览正常返回并将相关行标记为“供应商不能为空”。
- Excel 导入上线防误操作已实现第一版并覆盖全部 4 个入口：商品上传预览与 Confirm、供应商上传预览与 Confirm、类目原子导入、投标项目 Excel 创建。处理期间以前端全屏遮罩锁定交互，阻止站内路由切换，并对刷新或关闭页面请求浏览器原生确认；成功、失败或超时后自动解锁。该实现是紧急上线用的页面级保护，导入仍依赖当前页面请求，长期后台异步任务化尚未实施。

## Workstreams / Implementation Context

- Free Recommendation V4 Hard-filter Recall：新 Run 只做一次受控需求解析，服务端全量持久化符合数值硬条件的候选；无类目方向、无 30 条上限、无 AI 排序或逐条理由。候选 API 服务端分页，支持本页及全部待确认候选的范围确认；DeepSeek 结构化输出仍仅自动纠错重试一次。无 Migration，前端既有 `run.error` 展示合同不变。
- Free Recommendation Template Mapping UI：新增只读模板结构查询，映射页按上传表头逐列选择商品主数据来源字段；新 Run 的候选快照覆盖全部正式商品导出字段，保证模板可选字段具备稳定的历史导出数据。历史 Run 不反查当前 Product 补值。

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
- Web Admin Data Refresh：统一 API 客户端已设置 `cache: no-store`；Product List 的导入确认、停用、启用、永久删除成功后统一重新请求后端，清空跨页导出选择；导入回第一页，移除当前页最后一条时回上一页。递增请求序列阻止旧慢 GET 覆盖 mutation 后的新列表。Product Detail 保持 API 返回值即时回写；前端测试、类型检查和生产构建已验证。
- Web Admin LAN HTTP：统一 HTTP 客户端的请求 ID 在普通 HTTP 局域网 IP 的非安全浏览器上下文中可回退生成，避免 `crypto.randomUUID()` 不可用而在 `fetch` 前中断登录等 API 调用；该回退不用于认证或安全令牌。
- Category Management：基于既有 `scm_category` 三级维表补齐列表、详情、新增、编辑、删除、启用选择和 Excel 导入；商品不再引用该表，删除不再因 Product 被阻止。
