# Product / Category / Pricing Schema Review

状态：SCHEMA REVIEW READY
范围：一期商品、三级类目与当前价格快照的数据库结构评审稿；不包含 Migration、ORM、API、UI 或 Pricing Service。

## 术语与评审结论

- **FROZEN**：已由业务确认，不得在本评审中改变。
- **RECOMMENDED**：本评审建议，待 Schema Review 通过后才可写入 Migration。
- **PENDING**：现有资料不足，不得自行猜测或实现。

### FROZEN 基线

- 一行整理后的商品大表等于一条具体正式 `scm_product`；系统 `id` 是唯一主键，一期不强制 SPU/SKU。
- `model`、`sku`、`product_name`、`brand + model`、货号与69码均不设业务 UNIQUE；69码以原始文本保存，不拆颜色、不限制 13 位数字。
- Product、Supplier Master、Supplier Product Quote 是独立领域。商品大表“供应商”列不得生成 `product → supplier` 关系或报价。
- Product 通过 `category_id` 查询 Category 的 `deduction_rate`，并保存本次使用的 `deduction_rate` 快照。
- 所有金额和比率计算使用 Decimal、结果保留 4 位小数；派生价格结果需要正式保存。后端按 Category 规则重算并校验前端值。

## 推荐总体结构

**RECOMMENDED：**一期建立 `scm_category` 与 `scm_product` 两张正式表；当前价格输入、扣点快照和派生结果直接承载于 `scm_product`。这对应一行大表一条商品、无独立 Product Price History 的已知需求，令导入、列表筛选和排序为单表读取。

方案 B（`scm_product` 加独立 Product Pricing Table）会为当前价格增加关联、导入事务和查询复杂度；只有未来冻结多版本商品价格历史、价格生效区间或独立定价审批时才应引入。它不能与 Supplier Product Quote History 合并，后者仍是独立领域。

**FROZEN — General monetary / ratio rounding：**普通金额字段和普通比率字段以 Decimal 语义使用 `ROUND_HALF_UP`，统一保留 4 位小数（例如 `123.45678 → 123.4568`）；禁止 Float。

**FROZEN — `deduction_review` exception：**唯一例外使用 `ROUND_DOWN` / `ROUNDDOWN`，统一保留 4 位小数。

## 31 列 Product Schema Matrix

以下 Matrix 中，`UNIQUE` 均为数据库业务唯一约束；`—` 表示不适用。Nullable/Default 是 **RECOMMENDED**，不是现有实现。

| # | Excel字段 | 正式字段 / 处理目标 | MySQL Type | Nullable | Default | Index | Unique | 分类 | 备注 |
|---:|---|---|---|---|---|---|---|---|---|
| 1 | 上架日期 | `listed_at` | `DATE` | YES | `NULL` | YES | NO | MASTER_INPUT | 来源是否业务必填尚未确认；索引支持按上架日期筛选。 |
| 2 | 品牌 | `brand` | `VARCHAR(128)` | YES | `NULL` | YES | NO | MASTER_INPUT | 不自动拆品牌表。 |
| 3 | 图片 | `image_reference` | `VARCHAR(2048)` | YES | `NULL` | NO | NO | SOURCE_REFERENCE | 仅保留来源图片引用；URL、文件路径或多图语义 PENDING。 |
| 4 | 型号 | `model` | `VARCHAR(255)` | YES | `NULL` | YES | NO | MASTER_INPUT | 大小写敏感检索策略 PENDING；不得设唯一。 |
| 5 | sku | `sku` | `VARCHAR(255)` | YES | `NULL` | YES | NO | MASTER_INPUT | 不是系统 id。 |
| 6 | 商品名称 | `product_name` | `VARCHAR(512)` | YES | `NULL` | YES | NO | MASTER_INPUT | 不因样例推断唯一或必填。 |
| 7 | 一级类目 | `category_id` 解析输入 | `CHAR(36)` | YES | `NULL` | YES | NO | CATEGORY_LOOKUP | 不在 Product 重复保存名称；导入以三级路径匹配 Category。 |
| 8 | 二级类目 | `category_id` 解析输入 | `CHAR(36)` | YES | `NULL` | YES | NO | CATEGORY_LOOKUP | 与一级/三级共同用于受控类目匹配。 |
| 9 | 三级类目 | `category_id` FK | `CHAR(36)` | YES | `NULL` | YES | NO | CATEGORY_LOOKUP | FK 指向 `scm_category.id`；导入无法匹配时作为错误而非静默入库。 |
| 10 | 货号 | `item_number` | `VARCHAR(255)` | YES | `NULL` | YES | NO | MASTER_INPUT | 按源值保留，不是系统标识。 |
| 11 | 同款京东链接 | `jd_same_product_url` | `VARCHAR(2048)` | YES | `NULL` | NO | NO | SOURCE_REFERENCE | 与“参考链接”是两个来源列；未确认相同前分别保留。 |
| 12 | *成本价 | `cost_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | MASTER_INPUT | 后端定价基础输入。 |
| 13 | *市场价 | `market_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为 `jd_price + 10`；旧 Excel 值仅作导入差异检查。 |
| 14 | *京东价 | `jd_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | MASTER_INPUT | `jd_margin` 分母；零值处理由后端确定性校验。 |
| 15 | *慧采价/协议价 | `agreement_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为 `cost_price * 1.2`。 |
| 16 | 协议价采购价/结算价 | `agreement_purchase_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值由协议价及扣点快照计算。 |
| 17 | 利润 | `profit` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为结算价减成本价。 |
| 18 | 京东价毛利（15-50） | `jd_margin` | `DECIMAL(9,4)` | YES | `NULL` | YES | NO | DERIVED | 正式公式为 `(jd_price - agreement_purchase_price) / jd_price`；表头括号不替代公式。 |
| 19 | 采销员 | `purchasing_agent` | `VARCHAR(128)` | YES | `NULL` | YES | NO | MASTER_INPUT | 仅保留来源人员文本；不假定关联系统用户。 |
| 20 | 供应商 | 导入暂存来源值 | `VARCHAR(255)` | YES | `NULL` | NO | NO | IMPORT_ONLY | 不进入 `scm_product`；不得映射 `supplier_id`、建立 `scm_product → scm_supplier` FK 或自动创建 Supplier Product Quote。 |
| 21 | 69码 | `barcode_text` | `VARCHAR(255)` | YES | `NULL` | YES | NO | MASTER_INPUT | 原样文本，例如可含 `---深蓝`。 |
| 22 | 毛利复核 | `deduction_review` | `DECIMAL(9,4)` | YES | `NULL` | YES | NO | DERIVED | `ROUNDDOWN((agreement_price - agreement_purchase_price) / agreement_price, 4)`。 |
| 23 | 产品规格 | `product_specification` | `TEXT` | YES | `NULL` | NO | NO | MASTER_INPUT | 不根据文本自动拆参数表。 |
| 24 | 众诚毛利 | `gross_margin` | `DECIMAL(9,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为 `profit / agreement_price`。 |
| 25 | 备注 | `remark` | `TEXT` | YES | `NULL` | NO | NO | MASTER_INPUT | 普通业务文本。 |
| 26 | 折扣率 | `discount_rate` | `DECIMAL(9,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为 `agreement_price / jd_self_operated_price`。 |
| 27 | 限售区域 | `restricted_regions` | `TEXT` | YES | `NULL` | NO | NO | MASTER_INPUT | 原样业务文本；区域结构化规则 PENDING。 |
| 28 | 京东自营前台价 | `jd_self_operated_price` | `DECIMAL(18,4)` | YES | `NULL` | YES | NO | MASTER_INPUT | 当前活动到手价，不含国补价；不是计算字段。 |
| 29 | 参考链接 | `reference_url` | `VARCHAR(2048)` | YES | `NULL` | NO | NO | MASTER_INPUT | 优先同款京东自营旗舰店，无则同款京东自营商品。 |
| 30 | 偏远地区加收运费发货（具体另外核算） | `remote_area_freight_note` | `TEXT` | YES | `NULL` | NO | NO | SOURCE_REFERENCE | 仅保留来源说明；具体核算规则未冻结，不进入当前价格公式。 |
| 31 | 价格虚高比例（30%） | `price_inflation_rate` | `DECIMAL(9,4)` | YES | `NULL` | YES | NO | DERIVED | 正式值为 `(agreement_price - jd_self_operated_price) / jd_self_operated_price`；表头括号不替代公式。 |

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

**RECOMMENDED 约束：**商城类目建立 `UNIQUE(source_type, level3_external_id)` 来源数据唯一约束；工业品建立 `(source_type, level1_name, level2_name, level3_name)` 唯一索引，以冻结的“完全重复路径去重”规则实施。Migration 前需以真实数据预检上述约束是否存在冲突。

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
| `category_id` | `CHAR(36)` | YES / `NULL` | 索引；FK → `scm_category.id` | 不冗余保存三级名称；无匹配类目应在导入预览中报错。 |
| `deduction_rate` | `DECIMAL(9,4)` | YES / `NULL` | 索引 | 商品本次计算采用的类目扣点快照。 |
| `created_by`, `updated_by` | `CHAR(36)` | YES / `NULL` | NO | 系统审计字段。 |
| `created_at`, `updated_at` | `DATETIME` | NOT NULL / 当前时间 | 索引（`created_at`） | 系统审计字段。 |

Product 不重复存储一级、二级、三级类目名称：这是 Category 维度的职责，避免无理由冗余与更新不一致。若未来为历史快照、检索性能或导入追溯提出冗余，需要单独说明读写所有权和一致性策略。

**PENDING：**Product / Category 的逻辑删除策略、外键删除动作、来源图片的存储形态、品牌与采销员的结构化关系、类目匹配失败的人工修正流程，以及各输入字段的最终业务必填规则。不得在 C1 Migration 中自行决定。

## Decimal Precision / Scale Recommendation

| 字段组 | 推荐类型 | 理由 |
|---|---|---|
| 金额：`cost_price`、`jd_price`、`jd_self_operated_price`、`market_price`、`agreement_price`、`agreement_purchase_price`、`profit` | `DECIMAL(18,4)` | 支持 14 位整数与 4 位小数，覆盖高价值工业品、汇总前单品金额和冻结的四位结果；不使用 Float。业务最大金额尚未给出，实施前如有超范围资料应复审。 |
| 比率：`deduction_rate`、`jd_margin`、`deduction_review`、`gross_margin`、`discount_rate`、`price_inflation_rate` | `DECIMAL(9,4)` | 保留四位小数，并允许利润率、折扣率或虚高比例超过 1；`deduction_rate` 当前仅为 0.0500 / 0.0800。 |

所有除零场景须由后端确定性校验：`jd_price`、`agreement_price`、`jd_self_operated_price` 作为分母为零时不得产生除零结果。普通金额和比率使用上述冻结的 `ROUND_HALF_UP` / scale 4；仅 `deduction_review` 使用 `ROUND_DOWN` / scale 4。

## 后续实施顺序

Schema Review 通过后：冻结 Category / Product / Pricing 结构 → 实现 Pricing Service 与单元测试 → 基于届时最新 main 的 Alembic Head 创建 Category/Product Migration → 创建 Product Backend。Product Import、Supplier 与 Supplier Quote 不在本阶段实现范围。
