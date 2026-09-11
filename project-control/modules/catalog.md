# 商品主数据 / Catalog

状态：IMPLEMENTED / PRODUCT_DISABLE_AND_PERMANENT_DELETE
Owner：codex/product-disable-permanent-delete
Last Updated：2026-09-11

## Database
- [x] `20260909_0008` / `20260909_0009` 创建并对齐 `scm_category` 与 `scm_product`
- [x] `20260910_0013` 创建 Product Import Staging、供应商匹配决策及任务状态表；`20260910_0014` 支持 Product 直接保存三级类目原文；`20260910_0015` 增加导入图片暂存键
- [x] Product → Category、Product → Source Supplier 均为 `RESTRICT` 外键
- [x] `20260911_0018` 增加 `UNIQUE(source_supplier_id, sku)`；迁移会先拒绝历史重复键，禁止静默清理
- [x] `20260911_0020` 以 `ACTIVE` / `DISABLED` 替代 Product 逻辑删除，增加停用审计、永久删除审计及 `product:disable` / `product:purge` 权限
- [x] 未创建独立 Supplier Product Quote 表或报价历史表

## Backend
- [x] Pricing Service（定价服务）已实现
- [x] Product 查询、详情、基础资料编辑与成本价更新 API
- [x] Product 列表支持按 `source_supplier_id` 精确过滤，作为供应商详情页“相关商品”的唯一数据入口
- [x] 成本价更新在同一事务中调用 Pricing Service 并保存全部派生值
- [x] 固定 32 列商品大表导入、直接保存类目/价格正式值、保存 WPS/Excel 内嵌图片、严格供应商精确匹配、SKU 防重预览和全批次 Confirm
- [x] Supplier 为 `STOPPED` / `BLACKLIST` / 逻辑删除时，关联 Product 不能列表、详情、编辑或更新成本价；恢复 `NORMAL` 后自动恢复可见
- [x] Product 可显式停用/启用；停用商品不能正常列表、详情、编辑或更新成本价，但保留业务键和商品字段
- [x] 仅已停用 Product 可永久删除；删除前写入最小审计并依赖事务及外键保护，永久删除后同键可重新导入为新商品
- [x] Product Import 对同来源供应商 + SKU 的停用商品报错并阻止 Confirm；不恢复、不覆盖，正常同键商品仍阻止导入

## Frontend
- [x] 商品列表、详情（含本地图片预览）、按权限显示的基础资料编辑/成本价更新及导入预览/供应商解析页面；商品列表首列显示本地图片缩略图及无图/加载失败占位，供应商详情可跳转至其相关商品的筛选列表
- [x] 商品列表支持正常/已停用状态筛选、停用/启用和 SKU/名称二次确认的永久删除；页面保留普通纵向滚动，左侧导航固定于视口左侧
- [x] 统一 API 请求禁用浏览器缓存，商品导入 Confirm 后重新加载列表可立即读取最新商品数据

## Permissions
- [x] `product:list`、`product:detail`、`product:update`、`product:cost:update`、`product:disable`、`product:purge`、`product:import`、`product:import:resolve`

## Tests
- [x] Pricing Unit Tests（定价单元测试）已完成
- [x] Product / Catalog Integration Tests（含导入预览与 Confirm）已完成

## Known Issues
- Category Source Data Preflight 已完成；商城 external ID UNIQUE 预检通过，工业品完整路径已按导入去重规则收口。依据 ADR-0010，Category Source Loader 不再阻止固定商品大表 Confirm。
- 停用商品只能显式启用；同键导入始终阻止。永久删除成功后可重新导入同键商品。未来若要批量以 Excel 覆盖已有商品，仍需独立 ADR。

## Next Step
维护真实模板中所需的有效 Supplier Master，并补齐空供应商；随后从 Product Import 页面重新预览并 Confirm。不得绕过供应商解析或新增独立报价库。

## 已冻结业务规则
- 商品大表是正式商品主数据来源；
- 大表一行 = 一条具体商品；
- 正式商品表核心为 `scm_product`；
- `scm_product.source_supplier_id CHAR(36) NOT NULL`、索引并 FK → `scm_supplier.id ON DELETE RESTRICT`；非唯一且仅表示商品大表来源供应商；
- `scm_product.category_id CHAR(36) NOT NULL`；正式 Confirm 必须完成类目解析，Product 通过该关系取得 `deduction_rate`；
- 一期不强制 SPU/SKU；
- 真实整理后商品大表已取得；系统 `id` 为商品主键；
- `source_supplier_id + sku` 为 Product 防重业务键，并由数据库 UNIQUE 强制；SKU 为空的历史数据不在本次 Migration 中自动改写，新的导入与编辑不允许 SKU 为空；
- `model`、`product_name`、`brand + model`、货号、69码均不设业务 UNIQUE；
- 69码按源文本原样保存，不拆分；
- 类目来源规则已冻结为“商城三级品类维表”和“工业品产品线”两类；真实数据预检已完成：商城 `UNIQUE(source_type, level3_external_id)` 通过，商城同名称路径不同 external ID 不得被全局路径 UNIQUE 约束；工业品完整路径仅作导入去重规则。蓝色三级类目扣点 5%，其余当前规则 8%；
- Pricing Rule 已冻结：Decimal、4 位小数；前端可计算并提交，后端必须按正式类目规则重算校验；
- `cost_price` 是商品当前成本价，也是当前供应商报价；供应商新报价不进入独立报价库，而是在后续 Product Backend 直接更新目标 Product 的 `cost_price`；
- 成本价更新必须在同一事务内重算并保存派生价格与毛利，使用既有 `updated_by`、`updated_at` 审计；不保存 Quote 历史、有效期、作废或多供应商比价；
- 派生价格与毛利字段需要正式保存；一期建议当前价格及派生值直接承载于 `scm_product`；
- 32 列最新大表字段映射、Category 三级维度建议、Product ↔ Category FK 与 Decimal 类型建议见 `docs/schema/product-category-pricing-schema-review.md`；
- Pricing Service 已实现：使用 Decimal，正式派生值统一 4 位小数；普通字段使用 `ROUND_HALF_UP`，唯一例外 `deduction_review` 使用 `ROUND_DOWN`；该 Service 仅产生 System Calculated Values。Excel Derived Values 的逐字段对账属于后续 Product Import；Excel 值不得静默覆盖系统公式。

## Current Gate

`IMPLEMENTED / PRODUCT_DISABLE_AND_PERMANENT_DELETE`：固定模板 Staging、Supplier Matching、供应商 + SKU 防重预览、权限和全批次 Confirm 已实现；Product 基础资料编辑、停用/启用、永久删除和 Supplier 合作状态可见性联动已实现。依据 ADR-0015，同键停用商品的导入会阻止 Confirm，只有永久删除后才能用新 Excel 创建同键商品。依据 ADR-0010，类目和价格直接以大表正式值写入 Product，空的 `scm_category` 不阻止 Confirm；空或不合格供应商仍不得绕过导入校验。Category Source Loader、覆盖式导入更新及无受控类目关联 Product 的独立成本价维护仍属后续范围。
