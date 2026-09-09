# Product Master Field Dictionary / 商品主数据字段门禁

状态：FROZEN — `SCHEMA_DESIGN_READY`  
范围：已确认商品大表字段语义、唯一性约束边界与价格字段设计；不创建 Migration、ORM 或正式表。

## 主数据边界

整理好的真实商品大表一行等于 `scm_product` 一条具体正式商品。每条商品由系统生成稳定且唯一的 `id` 作为主键；一期不依赖 Excel 字段作为数据库主键，也不强制 SPU/SKU 二层模型。

以下字段按源数据保留，但一期不得建立业务 UNIQUE 约束：`model`（型号）、`sku`、`product_name`、`brand + model`、货号、69码。

`category_id` 是正式 Product 的 FROZEN `CHAR(36) NOT NULL` 外键。商品导入 Confirm 必须完成类目解析，正式 Product 通过该关系读取 Category 的 `deduction_rate`；Product 不重复保存一级、二级、三级类目名称。

| 概念字段 | 冻结处理 |
|---|---|
| `sku` | 按来源保留；不是系统 id，不唯一；后续可按查询需求评审索引 |
| `model`、`product_name`、`brand + model` | 不因样例或经验推断唯一性 |
| 货号 | 按来源保留；不是系统唯一标识，不唯一 |
| 源69码文本 | 原样保存且不拆分；例如 `6933037205930---深蓝` 不强制为 13 位数字，也不拆出颜色字段；正式代码名可在 Schema 阶段定为 `source_barcode`、`barcode_text` 等不暗示纯标准条码的名称 |
| 商品供应商列 | 原始 Excel 名称保留为 Staging 的 `supplier_name_raw`；按确定性规则解析后，正式 `scm_product` 以 `source_supplier_id` FK 关联来源供应商。名称不是业务 FK，导入不创建供应商或供应商报价。 |

## 价格概念字段（需要正式保存）

派生值不仅用于页面展示，未来商品或受控 Product Pricing Structure 必须保存，支持搜索、筛选、排序、报价、统计和毛利分析。最终是否全部放入 `scm_product` 留待正式 Schema Review。

| 分类 | 概念字段 |
|---|---|
| 基础值 | `cost_price`、`jd_price`、`jd_self_operated_price`、`reference_url`、`category_id` |
| 规则快照 | `deduction_rate` |
| 派生值 | `market_price`、`agreement_price`、`agreement_purchase_price`、`profit`、`jd_margin`、`deduction_review`、`gross_margin`、`discount_rate`、`price_inflation_rate` |

金额与比率计算使用 `Decimal`，禁止 `float`；结果统一保留 4 位小数。最终数据库精度（例如 `DECIMAL(18,4)`）在 Schema 设计时确认。

## 商品导入边界

`标准商品大表 → 模板校验 → 字段校验 → 字典校验 → 重复/冲突校验 → 错误预览 → 人工确认 → scm_product`。

禁止 AI 猜表头或自动字段映射；禁止自动创建 Supplier Product Quote；错误行不得静默进入正式库。供应商先进入 Supplier Master；商品导入仅匹配已有有效供应商，全部来源供应商解析完成后才能确认进入正式库。
