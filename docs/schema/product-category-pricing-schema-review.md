# Product / Category / Pricing Schema Review

状态：PARTIALLY SUPERSEDED BY ADR-0010
范围：一期商品、三级类目与当前价格快照的数据库结构评审稿；不包含 Migration、ORM、API、UI 或 Pricing Service。

> 2026-09-10 起，ADR-0010 替代本评审中关于固定商品大表导入必须解析 `category_id`、不得保留三级类目原文、以及导入必须按公式重算价格的结论。实际实现以 `20260910_0014` 为准：Product 直接保存三级类目原文，`category_id` 可空；导入直接保存 Excel 价格值。Pricing Service 仍用于单独成本价更新。2026-09-11 的已确认补丁进一步冻结 `source_supplier_id + sku` 为 Product 防重业务键，见 `20260911_0018`。

## 术语与评审结论

- **FROZEN**：已由业务确认，不得在本评审中改变。
- **RECOMMENDED**：本评审建议，待 Schema Review 通过后才可写入 Migration。
- **PENDING**：现有资料不足，不得自行猜测或实现。
- **BUSINESS_DECISION_REQUIRED**：需要业务方明确选择；C1 不得以“通常做法”代替决策。

### FROZEN 基线

- 一行整理后的商品大表等于一条具体正式 `scm_product`；系统 `id` 是唯一主键，一期不强制 SPU/SKU。
- `source_supplier_id + sku` 为 Product 防重业务键，并以数据库 UNIQUE 强制；`model`、`product_name`、`brand + model`、货号与69码仍不设业务 UNIQUE。69码以原始文本保存，不拆颜色、不限制 13 位数字。
- Product 与 Supplier Master 是独立领域。商品大表“供应商”列用于解析来源供应商；正式 Product 保存 `source_supplier_id`。`cost_price` 是 Product 当前成本价和当前供应商报价，不创建独立 Quote 领域。
- Product 通过 `category_id` 查询 Category 的 `deduction_rate`，并保存本次使用的 `deduction_rate` 快照。
- 所有金额和比率计算使用 Decimal、结果保留 4 位小数；派生价格结果需要正式保存。后端按 Category 规则重算并校验前端值。

## 推荐总体结构

**RECOMMENDED：**一期建立 `scm_category` 与 `scm_product` 两张正式表；当前价格输入、扣点快照和派生结果直接承载于 `scm_product`。这对应一行大表一条商品、无独立 Product Price History 的已知需求，令导入、列表筛选和排序为单表读取。

方案 B（`scm_product` 加独立 Product Pricing Table）会为当前价格增加关联、导入事务和查询复杂度；只有未来冻结多版本商品价格历史、价格生效区间或独立定价审批时才应引入。一期也不建设 Supplier Product Quote History。

**FROZEN — General monetary / ratio rounding：**普通金额字段和普通比率字段以 Decimal 语义使用 `ROUND_HALF_UP`，统一保留 4 位小数（例如 `123.45678 → 123.4568`）；禁止 Float。

**FROZEN — `deduction_review` exception：**唯一例外使用 `ROUND_DOWN` / `ROUNDDOWN`，统一保留 4 位小数。

## Schema Finalization Decision Matrix

| Decision | Current Evidence | Status | Final / Recommended Value | Migration Blocker? |
|---|---|---|---|---|
| `scm_product.category_id` nullability | 正式 Product 的唯一已冻结写入链路是 Import Confirm；Confirm 必须完成类目解析。定价亦必须经 `category_id` 查询正式 `deduction_rate`。 | FROZEN | `CHAR(36) NOT NULL`，FK → `scm_category.id`；不在 Product 重复存储三级名称。 | NO |
| Product lifecycle | ADR-0015 已冻结停用、启用、永久删除和同键导入行为。 | FROZEN | `status` 为 `ACTIVE` / `DISABLED`；停用保留业务键，永久删除后释放；不使用 Product 逻辑删除列。 | NO（Revision `20260911_0020` 已实施） |
| Category logical / physical delete | 现有来源只有“有效标记”，没有删除、恢复或历史保留语义。 | BUSINESS_DECISION_REQUIRED | C1 仅保留 `is_active`；不新增逻辑删除列，不定义物理删除 API。 | NO（删除模型不进入 C1） |
| Product → Category delete action | Cascade 会删除正式 Product，违反正式主数据保留原则；现有资料未把该动作提升为业务冻结规则。 | RECOMMENDED | `ON DELETE RESTRICT`；不得使用 `CASCADE`。 | NO |
| `source_supplier_id` | ADR-0008 已接受；Confirm 仅在来源供应商已解析且仍有效时写正式 Product。 | FROZEN | `CHAR(36) NOT NULL`、索引、FK → `scm_supplier.id ON DELETE RESTRICT`；单独不唯一，但与 `sku` 组成 Product 防重唯一键。 | NO |
| `brand` / `model` / `product_name` | 32 列最新商品大表确认字段语义与非唯一性，但没有业务必填规则。 | RECOMMENDED | `NULL`；不得因样例值齐全而改为 NOT NULL。 | NO |
| `cost_price` | 业务确认它就是当前供应商报价；正式 Product 的当前价格计算以它为基础。 | FROZEN | `DECIMAL(18,4) NOT NULL`；供应商新报价直接更新此值并重算派生价格。 | NO |
| `jd_price` / `jd_self_operated_price` | 是价格计算输入；现有资料冻结了公式和除零校验，未冻结所有 Product 都必须拥有这两项输入。 | RECOMMENDED | `NULL`；Pricing 保存/Confirm 时再按所用公式校验需要的输入。 | NO |
| Category unique constraints | 两份真实类目源数据预检已完成；商城 external ID 无重复，但商城有两组同路径不同 external ID。 | RECOMMENDED | 仅商城建立 `UNIQUE(source_type, level3_external_id)`；工业品完整路径为 Source Loader / Import 去重规则，不建全局数据库路径 UNIQUE。 | NO，预检已完成 |
| `source_type` | 现有资料有商城三级类目与工业品产品线两种来源。 | RECOMMENDED | `VARCHAR(32) NOT NULL`，受控值 `MALL_LEVEL3` / `INDUSTRIAL_LINE`。 | NO |
| Category `is_active` | 商城来源含有效标记；当前没有独立删除语义。 | RECOMMENDED | `BOOLEAN NOT NULL DEFAULT TRUE`，表达当前可用性而非逻辑删除。 | NO |
| `deduction_rate` | 类目扣点规则已冻结：商城标蓝 5%，其余商城及未标记工业品 8%。 | FROZEN | 值只从正式 Category 读取；Product 保存使用值快照。 | NO |
| Decimal precision | 现有评审已完成精度建议，尚非业务最大金额的正式上限承诺。 | RECOMMENDED | 金额 `DECIMAL(18,4)`；比率 `DECIMAL(9,4)`。 | NO |
| Rounding | 类目与价格规则门禁已冻结。 | FROZEN | 普通金额/比率 `ROUND_HALF_UP`、4 位小数；仅 `deduction_review` 为 `ROUND_DOWN`、4 位小数。 | NO |

## 32 列 Product Schema Matrix

以下 Matrix 中，`UNIQUE` 均为数据库业务唯一约束；`—` 表示不适用。Nullable/Default 是 **RECOMMENDED**，不是现有实现。

| # | Excel字段 | 正式字段 / 处理目标 | MySQL Type | Nullable | Default | Index | Unique | 分类 | 备注 |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | 上架日期 | `listed_at` | `DATE` | YES | `NULL` | YES | NO | MASTER_INPUT | 来源是否业务必填尚未确认；索引支持按上架日期筛选。 |
| 2 | 品牌 | `brand` | `VARCHAR(128)` | YES | `NULL` | YES | NO | MASTER_INPUT | 不自动拆品牌表。 |
| 3 | 图片 | `image_reference` | `VARCHAR(2048)` | YES | `NULL` | NO | NO | SOURCE_REFERENCE | 仅保留来源图片引用；URL、文件路径或多图语义 PENDING。 |
| 4 | 型号 | `model` | `VARCHAR(255)` | YES | `NULL` | YES | NO | MASTER_INPUT | 大小写敏感检索策略 PENDING；不得设唯一。 |
| 5 | sku | `sku` | `VARCHAR(255)` | YES | `NULL` | YES | NO | MASTER_INPUT | 不是系统 id。 |
| 6 | 商品名称 | `product_name` | `VARCHAR(512)` | YES | `NULL` | YES | NO | MASTER_INPUT | 不因样例推断唯一或必填。 |
| 7 | 一级类目 | 三级路径解析输入（不是 `scm_product` 列） | — | PENDING | — | NO | NO | CATEGORY_LOOKUP | 不在 Product 重复保存名称；导入字段级必填规则尚未冻结。 |
| 8 | 二级类目 | 三级路径解析输入（不是 `scm_product` 列） | — | PENDING | — | NO | NO | CATEGORY_LOOKUP | 与一级/三级共同用于受控类目匹配；导入字段级必填规则尚未冻结。 |
| 9 | 三级类目 | `category_id` FK | `CHAR(36)` | NO | — | YES | NO | CATEGORY_LOOKUP | 正式 Product 为 NOT NULL；FK 指向 `scm_category.id`；导入无法匹配时作为错误而非静默入库。 |
| 10 | 货号 | `item_number` | `VARCHAR(255)` | YES | `NULL` | YES | NO | MASTER_INPUT | 按源值保留，不是系统标识。 |
| 11 | 链接 | `jd_same_product_url` | `VARCHAR(2048)` | YES | `NULL` | NO | NO | SOURCE_REFERENCE | 与“参考链接”是两个来源列；不合并。 |
| 12 | *成本价 | `cost_price` | `DECIMAL(18,4)` | NO | — | YES | NO | MASTER_INPUT | FROZEN：当前成本价，也是当前供应商报价；后端定价基础输入。 |
| 13 | *市场价 | `market_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为 `jd_price + 10`；旧 Excel 值仅作导入差异检查。 |
| 14 | *京东价 | `jd_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | MASTER_INPUT | `jd_margin` 分母；零值处理由后端确定性校验。 |
| 15 | *慧采价/协议价 | `agreement_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为 `cost_price * 1.2`。 |
| 16 | 协议价采购价/结算价 | `agreement_purchase_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值由协议价及扣点快照计算。 |
| 17 | 利润 | `profit` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为结算价减成本价。 |
| 18 | 京东价毛利（30-50） | `jd_margin` | `DECIMAL(9,4)` | YES | `NULL` | YES | NO | DERIVED | 正式公式为 `(jd_price - agreement_purchase_price) / jd_price`；表头括号不替代公式。 |
| 19 | 毛利复核 | `deduction_review` | `DECIMAL(9,4)` | YES | `NULL` | YES | NO | DERIVED | `ROUNDDOWN((agreement_price - agreement_purchase_price) / agreement_price, 4)`。 |
| 20 | 众诚毛利 | `gross_margin` | `DECIMAL(9,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为 `profit / agreement_price`。 |
| 21 | 采销员 | `purchasing_agent` | `VARCHAR(128)` | YES | `NULL` | YES | NO | MASTER_INPUT | 仅保留来源人员文本；不假定关联系统用户。 |
| 22 | 供应商 | Staging：`supplier_name_raw`；正式：`source_supplier_id` | 原值 `VARCHAR(255)`；FK `CHAR(36)` | 原值 YES；正式 NOT NULL | `NULL` / — | 正式 FK 索引 | NO | SOURCE_SUPPLIER_LOOKUP | 原值仅供导入审计与确定性解析；正式 FK → `scm_supplier.id`，`ON DELETE RESTRICT`。不是当前报价供应商；不创建独立 Quote。 |
| 23 | 69码 | `barcode_text` | `VARCHAR(255)` | YES | `NULL` | YES | NO | MASTER_INPUT | 原样文本，例如可含 `---深蓝`。 |
| 24 | 产品规格 | `product_specification` | `TEXT` | YES | `NULL` | NO | NO | MASTER_INPUT | 不根据文本自动拆参数表。 |
| 25 | 卖点 | `selling_points` | `TEXT` | YES | `NULL` | NO | NO | MASTER_INPUT | 原样保留商品卖点文本；不自动拆关键词或标签表。 |
| 26 | 限售区域 | `restricted_regions` | `TEXT` | YES | `NULL` | NO | NO | MASTER_INPUT | 原样业务文本；区域结构化规则 PENDING。 |
| 27 | 京东自营前台价 | `jd_self_operated_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | MASTER_INPUT | 当前活动到手价，不含国补价；不是计算字段。 |
| 28 | 参考链接 | `reference_url` | `VARCHAR(2048)` | YES | `NULL` | NO | NO | MASTER_INPUT | 原样保留该来源链接。 |
| 29 | 自营旗舰店/官方旗舰店 | `storefront_type` | `VARCHAR(64)` | YES | `NULL` | NO | NO | MASTER_INPUT | 原样保留店铺类型文本；枚举值尚未冻结，不强加约束。 |
| 30 | 折扣率 | `discount_rate` | `DECIMAL(9,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为 `agreement_price / jd_self_operated_price`。 |
| 31 | 价格虚高比例（30%） | `price_inflation_rate` | `DECIMAL(9,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为 `(agreement_price - jd_self_operated_price) / jd_self_operated_price`；表头括号不替代公式。 |
| 32 | 备注 | `remark` | `TEXT` | YES | `NULL` | NO | NO | MASTER_INPUT | 普通业务文本。 |

所有 DERIVED 列的旧 Excel 值只能用于导入校验/差异展示，不能覆盖后端按冻结公式重新计算的正式值。

## RECOMMENDED `scm_category`

| 字段 | MySQL Type | Nullable / Default | Index / Unique | 说明 |
|---|---|---|---|---|
| `id` | `CHAR(36)` | NOT NULL / 系统生成 | PK | 遵循 ADR-0006 `UUIDChar36`。 |
| `source_type` | `VARCHAR(32)` | NOT NULL / — | 索引 | 建议受控来源值 `MALL_LEVEL3`、`INDUSTRIAL_LINE`；不以 Excel 颜色判定运行时规则。 |
| `level1_external_id` | `VARCHAR(128)` | YES / `NULL` | NO | 商城来源 ID；工业品无稳定 ID 时为空。 |
| `level1_name` | `VARCHAR(255)` | NOT NULL / — | NO | 三级路径组成部分。 |
| `level2_external_id` | `VARCHAR(128)` | YES / `NULL` | NO | 同上。 |
| `level2_name` | `VARCHAR(255)` | NOT NULL / — | NO | 三级路径组成部分。 |
| `level3_external_id` | `VARCHAR(128)` | YES / `NULL` | 唯一索引（与 `source_type`） | 商城三级 External Category ID；工业品可为空。 |
| `level3_name` | `VARCHAR(255)` | NOT NULL / — | 索引 | Product 的最终匹配维度。 |
| `deduction_rate` | `DECIMAL(9,4)` | NOT NULL / `0.0800` | NO | 蓝色商城三级类目为 `0.0500`，其余及未标记工业品当前为 `0.0800`。 |
| `is_active` | `BOOLEAN` | NOT NULL / `TRUE` | 索引 | 映射商城“有效标记”。 |
| `shelf_flag` | `VARCHAR(32)` | YES / `NULL` | NO | 原样保留商城“上下柜标记”；具体枚举 PENDING。 |
| `business_unit` | `VARCHAR(128)` | YES / `NULL` | 索引 | 原样保留商城“主营事业部”。 |
| `created_by`, `updated_by` | `CHAR(36)` | YES / `NULL` | NO | 与既有系统审计字段一致。 |
| `created_at`, `updated_at` | `DATETIME` | NOT NULL / 当前时间 | NO | 与既有系统审计字段一致。 |

**RECOMMENDED 约束：**商城类目建立 `UNIQUE(source_type, level3_external_id)` 来源数据唯一约束；真实数据预检已通过。不得在整个 `scm_category` 建立 `UNIQUE(source_type, level1_name, level2_name, level3_name)`：商城存在合法的同名称路径、不同三级 external ID。工业品完整三级路径只作为 Category Source Loader / Import 的确定性去重与冲突检查规则；C1 Migration 暂不建立该路径数据库唯一索引，也不得为条件唯一性自行加入 generated column、functional index、trigger 或其他复杂机制。

工业品完整三级名称路径仅用于导入去重与冲突检测，不是永久不可变的业务身份。所有正式 Category 身份始终使用 `scm_category.id`。

## FROZEN Category Deduction Runtime Rule

不同类目的价格差异当前只通过正式 `scm_category.deduction_rate` 体现：

`Product.category_id → scm_category.id → scm_category.deduction_rate → Pricing calculation`

- 商城标蓝三级类目：`deduction_rate = 0.0500`。
- 商城其他三级类目：`deduction_rate = 0.0800`。
- 工业品未明确标记为 5%：`deduction_rate = 0.0800`。

Pricing Service 只能接受从 `scm_category` 查询得到的 `deduction_rate`，不得按一级、二级或三级类目名称判断，不得读取 Excel 颜色，也不得在 Python 中硬编码若干类目为 5% 或 8%。`scm_product.deduction_rate` 同时保存本次计算实际使用的快照；Category 日后调整扣点时，既有商品的历史计算结果仍可解释。

## RECOMMENDED `scm_product`

除 Matrix 已列出的 Product 正式字段外，推荐下列系统列：

| 字段 | MySQL Type | Nullable / Default | Index / Unique | 说明 |
|---|---|---|---|---|
| `id` | `CHAR(36)` | NOT NULL / 系统生成 | PK | UUID 主键，非 Excel 字段。 |
| `category_id` | `CHAR(36)` | NOT NULL / — | 索引；FK → `scm_category.id`，RECOMMENDED `ON DELETE RESTRICT` | 不冗余保存三级名称；正式 Confirm 必须完成类目解析，无匹配类目应在导入预览中报错。 |
| `source_supplier_id` | `CHAR(36)` | NOT NULL / — | 索引；FK → `scm_supplier.id`，ON DELETE RESTRICT | 来源供应商，不是唯一供应商；Confirm 前必须完成解析，故正式 Product 不允许 unresolved supplier。 |
| `deduction_rate` | `DECIMAL(9,4)` | YES / `NULL` | 索引 | 商品本次计算采用的类目扣点快照。 |
| `created_by`, `updated_by` | `CHAR(36)` | YES / `NULL` | NO | 系统审计字段。 |
| `created_at`, `updated_at` | `DATETIME` | NOT NULL / 当前时间 | 索引（`created_at`） | 系统审计字段。 |

Product 不重复存储一级、二级、三级类目名称：这是 Category 维度的职责，避免无理由冗余与更新不一致。若未来为历史快照、检索性能或导入追溯提出冗余，需要单独说明读写所有权和一致性策略。

`source_supplier_id` 不设 UNIQUE；一个供应商可对应许多商品。供应商名称的正式快照字段不在本轮冻结，如将来确需 `source_supplier_name` 或 `supplier_name_snapshot`，须另行评审。

## RECOMMENDED Supplier Match Decision and Confirm Gate

推荐 `scm_product_import_supplier_match`：`id CHAR(36) PK`、`import_task_id CHAR(36) NOT NULL FK -> scm_import_task.id`、`supplier_name_normalized VARCHAR(255) NOT NULL`、`match_status VARCHAR(...) NOT NULL`、`match_method VARCHAR(...) NULL`、`matched_supplier_id CHAR(36) NULL FK -> scm_supplier.id ON DELETE RESTRICT`、`resolved_by CHAR(36) NULL`、`resolved_at DATETIME NULL`、`created_at`、`updated_at`；建立 `UNIQUE(import_task_id, supplier_name_normalized)`。`match_status` 为 `MATCHED`、`AMBIGUOUS`、`UNMATCHED` 或 `INELIGIBLE`；`match_method` 为 `NAME_EXACT` 或 `MANUAL`，未成功时为 NULL，`MATCHED` 必须有 `matched_supplier_id`。不保存 candidate IDs JSON 或候选数量快照，候选从当前 Supplier Master 查询。

Import Row 尚未冻结时，推荐增加 `supplier_match_id` FK 指向该表，使同一批次、同一标准化供应商名称的行共享一项决策。自动匹配只允许 NFKC、trim、连续空白压缩；仅在名称相等且唯一有效候选（ARCHIVED + NORMAL + not deleted）时写 `MATCHED/NAME_EXACT`。多候选、无同名、同名均无效分别为 `AMBIGUOUS`、`UNMATCHED`、`INELIGIBLE`，只能人工从当前有效供应商选择或在 Supplier Master 处理后重试。

Confirm 是 all-or-nothing：重新校验行、类目、价格、全部决策均为 `MATCHED`，并重新查询每个已匹配供应商仍有效；任一失败均不得写入任何 `scm_product`。因此匹配成功并不替代 Confirm 时的状态检查。

**BUSINESS_DECISION_REQUIRED：**Category 删除策略、未明确的外键删除动作、来源图片的存储形态、品牌与采销员的结构化关系、类目匹配失败的人工修正流程，以及除已冻结 `category_id`、`source_supplier_id`、`cost_price` 外的输入字段最终业务必填规则。Product 生命周期已由 ADR-0015 冻结；不得在 C1 Migration 中自行决定其余未冻结事项。

## Category Source Data Preflight

状态：COMPLETE。已对正式来源“商城三级品类维表数据.xlsx”与“工业品产品线.xlsx”完成预检。

### 商城三级品类维表

- 原始数据 6,289 行；一级、二级、三级名称及 `level3_external_id` 空值均为 0。
- `level3_external_id` 重复 0，完全重复行 0；`UNIQUE(source_type, level3_external_id)` 因此预检通过。
- 完整三级名称路径有 2 组重复：`电脑、办公 / 办公用纸 / 其他标签纸` 对应 external ID `35450`、`35638`；`休闲食品 / 蜜饯果干 / 混合蔬果干` 对应 `37058`、`37068`。正式商城 Category 身份必须以 external ID 为准；后续 Product Import 若仅以这两个名称路径匹配，必须标记 `AMBIGUOUS`，不得随机绑定。
- 蓝色三级类目 449 条，非蓝色 5,840 条；有效标记均为 `1`；上下柜标记 `1` 为 5,078 条、`0` 为 1,211 条。

### 工业品产品线

- 原始数据 578 行；一级、二级、三级名称空值均为 0。
- 发现 3 组完全重复完整路径：`工业品 / 工具 / 工具存储`、`五金/工具 / 搬运/起重设备 / 叉车配件`、`五金/工具 / 仪器仪表 / 检漏仪`。
- Source Loader 按完整三级路径去重后，正式路径数为 575；该路径是导入去重身份，不是永久不可变业务 ID。

### 预计正式数量与扣点

预计正式 `scm_category` 为 6,864 条：商城 6,289 条加工业品 575 条。`deduction_rate = 0.0500` 为商城蓝色 449 条；`0.0800` 为其他商城 5,840 条加工业品 575 条，共 6,415 条。

## C1 Migration Plan (plan only)

基线 Alembic Head 为 `20260908_0007`。真实类目源数据预检已完成；后续 Category / Product Migration 应只包含：

- `scm_category`；
- `scm_product`，包括 `category_id` 与 `source_supplier_id` 两个正式外键、冻结的价格快照与派生价格列；
- 本评审已列出的索引、Decimal 精度及商城 `UNIQUE(source_type, level3_external_id)` 约束。

不得在同一个 Migration 创建 `scm_import_task`、`scm_import_row`、`scm_import_row_error` 或 `scm_product_import_supplier_match`；它们属于后续 Product Import。C1 也不得加入未经业务决策的 Product/Category 删除列。

## Decimal Precision / Scale Recommendation

| 字段组 | 推荐类型 | 理由 |
|---|---|---|
| 金额：`cost_price`、`jd_price`、`jd_self_operated_price`、`market_price`、`agreement_price`、`agreement_purchase_price`、`profit` | `DECIMAL(18,4)` | 支持 14 位整数与 4 位小数，覆盖高价值工业品、汇总前单品金额和冻结的四位结果；不使用 Float。业务最大金额尚未给出，实施前如有超范围资料应复审。 |
| 比率：`deduction_rate`、`jd_margin`、`deduction_review`、`gross_margin`、`discount_rate`、`price_inflation_rate` | `DECIMAL(9,4)` | 保留四位小数，并允许利润率、折扣率或虚高比例超过 1；`deduction_rate` 当前仅为 0.0500 / 0.0800。 |

所有除零场景须由后端确定性校验：`jd_price`、`agreement_price`、`jd_self_operated_price` 作为分母为零时不得产生除零结果。普通金额和比率使用上述冻结的 `ROUND_HALF_UP` / scale 4；仅 `deduction_review` 使用 `ROUND_DOWN` / scale 4。

## 后续实施顺序

Schema Finalization、Pricing Service 与类目数据预检已完成：基于届时最新 main 的 Alembic Head 创建 Category/Product Migration → 创建 Product Backend（包括成本价直接更新与派生价格原子重算）→ 创建 Product Import。Supplier Product Quote 不在一期范围。
