# 商品主数据 / Catalog

状态：IMPLEMENTED / PRODUCT_MASTER_CATEGORY_DECOUPLED / PRODUCT_IMPORT_SAFETY_CONCURRENCY
Owner：feat/product-import-safety-concurrency
Last Updated：2026-09-18

## Database
- [x] `20260909_0008` / `20260909_0009` 创建并对齐 `scm_category` 与 `scm_product`
- [x] `20260910_0013` 创建 Product Import Staging、供应商匹配决策及任务状态表；`20260910_0014` 支持 Product 直接保存三级类目原文；`20260910_0015` 增加导入图片暂存键
- [x] `20260918_0032` 删除 Product 与 Product Import Staging 的 `category_id`、类目外键和索引；Product → Source Supplier 保持 `RESTRICT` 外键
- [x] `20260911_0018` 增加 `UNIQUE(source_supplier_id, sku)`；迁移会先拒绝历史重复键，禁止静默清理
- [x] `20260911_0020` 以 `ACTIVE` / `DISABLED` 替代 Product 逻辑删除，增加停用审计、永久删除审计及 `product:disable` / `product:purge` 权限
- [x] `20260911_0022` 支持 Product Import 通过行分批确认，记录导入行状态与已导入计数
- [x] `20260916_0028` 新增类目列表、详情、新增、编辑、删除五项独立权限，并默认授予现有 `boss` 角色
- [x] `20260917_0028` 支持同来源供应商 + SKU 命中正常 Product 的重新导入更新，记录暂存行新增/更新类型与变更字段
- [x] `20260917_0029` 合并类目权限与商品重新导入更新的 Alembic Heads，不改业务 Schema 或数据
- [x] `20260917_0030` 增加 2026 商品大表的 11 个业务字段、销量/好评率约束及价格/折扣/销量筛选索引
- [x] `20260918_0031` 增加状态与三级类目路径的 Product Master 筛选索引（类目文本使用 128 字符索引前缀）
- [x] `20260918_0033` 增加导入行标准化正式值及 Product 乐观并发快照
- [x] `20260918_0034` 将六个正式价格字段扩展为 `DECIMAL(65,30)`，保留 Excel 价格原值；`20260920_0035` 将 `cost_price` 调整为可空
- [x] 未创建独立 Supplier Product Quote 表或报价历史表

## Backend
- [x] 价格字段作为独立正式商品主数据保存；成本价快捷更新不自动重算其他价格或比例（ADR-0024）
- [x] Product 综合搜索、文本/类目/数值区间查询、全字段详情、业务键只读编辑、受控图片上传/清除与成本价更新 API
- [x] Product List 类目候选直接从可见正式 Product 的三级路径去重取得；类目维表与商品导入、编辑完全脱钩
- [x] Product 列表支持按 `source_supplier_id` 精确过滤，作为供应商详情页“相关商品”的唯一数据入口
- [x] 成本价更新仅修改 `cost_price` 与审计字段；完整编辑和 Excel 导入/重新导入均逐字段保存正式价格值
- [x] 固定 43 列 2026 商品大表导入、三级类目必填文本校验与直接保存价格正式值、保存 WPS/Excel 内嵌图片、严格供应商精确匹配、SKU 防重预览和通过行原子 Confirm
- [x] Supplier 为 `STOPPED` / `BLACKLIST` / 逻辑删除时，关联 Product 不能列表、详情、编辑或更新成本价；恢复 `NORMAL` 后自动恢复可见
- [x] Product 可显式停用/启用；停用商品不能正常列表、详情、编辑或更新成本价，但保留业务键和商品字段
- [x] 类目维表管理：三级路径列表、详情、新增、编辑、删除、轻量启用选择接口与 Excel 原子导入；不再受 Product 引用保护，真实身份为 `source_type + level3_external_id`，路径仅为属性
- [x] 类目管理列表为服务端分页（默认每页 20）；商城导入使用公司 9 列中文模板，后端固定 `MALL_LEVEL3`，由批次 `deduction_rate_percent` 写入正式扣点，Excel 颜色不参与判断且不隐式更新既有类目
- [x] 仅已停用 Product 可永久删除；删除前写入最小审计并依赖事务及外键保护，永久删除后同键可重新导入为新商品
- [x] Product Import 对同来源供应商 + SKU 的正常商品标记为更新候选并在 Confirm 原子覆盖固定模板字段；停用商品仍报错并阻止 Confirm
- [x] 同键更新保留供应商与 SKU，其他 41 列按 Excel 覆盖且空值清空；成功提交后清理被替换的旧本地图片
- [x] 商品大表使用分块上传、临时文件和只读路径解析，默认允许 1GB / 100,000 行；`DISPIMG` 临时源文件保存与 Confirm 图片提取均避免整份工作簿读入内存；Confirm 逐张流式解码和落盘，不设全工作簿图片累计上限
- [x] `DISPIMG` 引用缺图、不支持或单图超过 `PRODUCT_IMPORT_MAX_IMAGE_MB`（默认 64MB）时行校验失败；TIFF/EMF/BMP/WMF 在保存前转为 PNG，避免正式 Product 指向浏览器无法显示的媒体
- [x] 商品导入表头校验兼容 Excel/WPS 末尾空白格式列；只允许批准的 43 个非空表头
- [x] 商品导入在预览阶段完成 Decimal/Pydantic 标准化；Confirm 批量锁定引用并校验 Product 版本，阻止不同任务对同供应商 + SKU 的静默覆盖
- [x] 重型工作簿操作默认每 API 进程并发 1，暂存行按 500 条批量写入；预览明细由数据库按状态分页
- [x] 大表 Confirm 的 Product 业务键查询/锁定按稳定顺序每 500 组分批执行；前端 Confirm 请求超时为 15 分钟，避免后端成功提交后浏览器 10 秒超时误报失败

## Frontend
- [x] 商品列表筛选支持一级、二级、三级类目直接搜索和多选；候选项来自可见 Product Master 路径，选择三级时自动回显对应一级、二级，选择二级时自动回显一级。页面首次进入不加载完整类目表，聚焦或搜索时远程获取每层最多 50 个选项；下拉滚动接近底部即自动继续读取下一批，并保留到底事件作为后备，更换关键词会重置结果。直接选择项按层级组成 OR 查询。商品编辑页使用三个必填、可输入且 Product Master 候选联动的类目文本字段。列表提供常用/高级可输入筛选和浏览器本地自定义列，详情和编辑覆盖 43 列业务字段，供应商/SKU 只读，图片通过文件上传维护
- [x] 导入预览显示已导入、已更新、通过、新增更新候选和不通过行，支持“更新”筛选并展示更新字段；商品页可下载批准的原始 43 列模板
- [x] 4,000+ 行导入预览使用每页 50 行的服务端分页，不再把全部行发送到浏览器
- [x] 商品列表支持正常/已停用状态筛选、停用/启用和 SKU/名称二次确认的永久删除；页面保留普通纵向滚动，左侧导航固定于视口左侧
- [x] 统一 API 请求禁用浏览器缓存，商品导入 Confirm 后重新加载列表可立即读取最新商品数据
- [x] 商品主数据增加“商品列表 / 操作记录”可切换页签；操作记录按商品展示图片、导入人、导入时间、最后更新人和最后更新时间，用户名从既有 `created_by` / `updated_by` 解析，未新增审计表
- [x] 类目管理页：与 Supplier 管理页统一的 Header / Card / Table 视觉结构，保留三级路径服务端分页、新增/编辑/删除确认、模板下载和 Excel 导入结果；用户侧统一填写“采购价系数”（如 `×0.95` 表示扣点 5%），精确转换为 API / DB 的 `deduction_rate = 0.05` 或 Import `deduction_rate_percent = "5"`。UI coefficient ≠ database deduction rate；正式 Pricing 公式仍为 `agreement_purchase_price = agreement_price × (1 - deduction_rate)`。
- [x] 类目管理列表：支持一级/二级/三级类目、主营事业部的服务端包含筛选，以及采购价系数（转换后对 `scm_category.deduction_rate` Decimal 精确匹配）和状态精确筛选；多条件为 AND，筛选后仍使用每页 20 条的服务端分页，COUNT 与列表使用相同 SQL 条件。
- [x] 类目管理菜单、路由和新增/编辑/删除按钮按独立类目权限显示；模板下载和 Excel 导入仍由 `product:import` 控制

## Permissions
- [x] `product:list`、`product:detail`、`product:update`、`product:cost:update`、`product:disable`、`product:purge`、`product:import`、`product:import:resolve`
- [x] `category:list`、`category:detail`、`category:create`、`category:update`、`category:delete`；类目选择接口保留 `product:list`，类目模板/导入保留 `product:import`

## Tests
- [x] Pricing Unit Tests（定价单元测试）已完成
- [x] Product / Catalog Integration Tests（含导入预览与 Confirm）已完成
- [x] 类目 CRUD 权限隔离、商品类目选择权限边界及前端菜单/路由/按钮权限契约测试已完成

## Known Issues
- 商品与类目维表已按 ADR-0026 脱钩。三级类目文本仍必须填写，但不再校验或回填 `scm_category`；类目维表暂保留为独立管理数据。
- 停用商品只能显式启用；同键停用商品仍阻止导入。永久删除成功后可重新导入同键商品。正常同键商品按 ADR-0020 允许固定模板重新导入更新。

## Next Step
维护真实模板中所需的有效 Supplier Master，并补齐空供应商；随后从 Product Import 页面重新预览并 Confirm。不得绕过供应商解析或新增独立报价库。

## 已冻结业务规则
- 商品大表是正式商品主数据来源；
- 大表一行 = 一条具体商品；
- 正式商品表核心为 `scm_product`；
- `scm_product.source_supplier_id CHAR(36) NOT NULL`、索引并 FK → `scm_supplier.id ON DELETE RESTRICT`；非唯一且仅表示商品大表来源供应商；
- Product Import 与手工编辑均必须填写 Product 自有的三级类目文本；不写入、查询或依赖 Category ID；
- 一期不强制 SPU/SKU；
- 真实整理后商品大表已取得；系统 `id` 为商品主键；
- `source_supplier_id + sku` 为 Product 防重业务键，并由数据库 UNIQUE 强制；SKU 为空的历史数据不在本次 Migration 中自动改写，新的导入与编辑不允许 SKU 为空；
- `model`、`product_name`、`brand + model`、货号、69码均不设业务 UNIQUE；
- 69码按源文本原样保存，不拆分；
- 类目维表来源规则仍适用于独立类目管理，但不再限制商品大表；商品大表只要求三级文本非空，允许路径不存在或重复；
- 六个价格字段使用 `DECIMAL(65,30)`，最多保留 30 位小数且不自动四舍五入；利润保持 4 位小数，成本价可为空，Excel 无法解析的正式数值写为 NULL；专用成本价维护接口提交时仍必须大于零（ADR-0030）；
- `cost_price` 是商品当前成本价，也是当前供应商报价；供应商新报价不进入独立报价库，而是在后续 Product Backend 直接更新目标 Product 的 `cost_price`；
- 成本价更新使用既有 `updated_by`、`updated_at` 审计，但不联动重算派生价格与毛利；不保存 Quote 历史、有效期、作废或多供应商比价；
- 派生价格与毛利字段需要正式保存；一期建议当前价格及派生值直接承载于 `scm_product`；
- 43 列 2026 大表字段映射及筛选/编辑规则见 `docs/data-gates/product-master-field-dictionary.md`；
- Excel 与手工维护的价格、利润和比例均为正式独立值；系统不以公式覆盖或校验其相互关系（ADR-0024）。

## Current Gate

`IMPLEMENTED / PRODUCT_MASTER_CATEGORY_DECOUPLED`：批准模板已升级为 43 列；新增字段、覆盖式重新导入、旧图片回收、组合筛选、Product Master 直接提供的三级类目多选与父级回显，以及首次不下载六千余条类目、远程选项每批最多 50 条且下拉续载已实现。三级类目为空、供应商空或不合格以及停用同键商品仍不得绕过导入校验；Category Master 的不存在、停用或重复不再阻止商品入库。
