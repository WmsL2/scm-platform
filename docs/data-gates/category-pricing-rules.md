# Category and Pricing Rules / 类目与价格规则门禁

状态：FROZEN — `SCHEMA_DESIGN_READY`  
范围：类目来源、扣点规则、价格公式与计算责任；本文件不创建 Category 或 Product Schema。

## 类目来源与扣点

真实来源为“商城三级品类维表数据.xlsx”与“工业品产品线.xlsx”。商城三级品类维表包含一级/二级/三级类目 ID 与名称、有效标记、上下柜标记、主营事业部。

- 商城三级类目优先保留来源三级类目 ID，作为 External Category ID。
- 工业品产品线若不存在稳定来源 ID，正式表使用系统生成内部 id；导入前对完全重复路径去重。
- 正式实现不得依赖 Excel 单元格颜色；蓝色仅是来源中的业务规则标记。
- 商城表中标蓝三级类目 `deduction_rate = 0.0500`，其他三级类目 `deduction_rate = 0.0800`。
- 工业品类目未明确标记为 5% 时，当前默认 `deduction_rate = 0.0800`。
- 扣点率必须通过正式 Category Table 数据查询取得，禁止在 Product/Pricing Python 中以类目 `if/else` 写死。

概念关系：`Product → category_id → Category → deduction_rate`。商品同时保存本次计算实际使用的 `deduction_rate` 快照，使类目规则日后变化仍可解释历史计算。

## 价格公式

所有金额计算使用 `Decimal`，结果统一保留 4 位小数。

| 字段 | 冻结公式或定义 |
|---|---|
| `market_price` | `jd_price + 10` |
| `agreement_price` | `cost_price * 1.2` |
| `agreement_purchase_price` | `agreement_price * (1 - deduction_rate)`；5% 为 `* 0.95`，8% 为 `* 0.92` |
| `profit` | `agreement_purchase_price - cost_price` |
| `jd_margin` | `(jd_price - agreement_purchase_price) / jd_price` |
| `deduction_review` | `ROUNDDOWN((agreement_price - agreement_purchase_price) / agreement_price, 4)`，并与采用的 `deduction_rate` 对照校验 |
| `gross_margin` | `profit / agreement_price` |
| `discount_rate` | `agreement_price / jd_self_operated_price` |
| `price_inflation_rate` | `(agreement_price - jd_self_operated_price) / jd_self_operated_price` |

`jd_price`、`agreement_price` 或 `jd_self_operated_price` 为零时，涉及其作分母的公式必须确定性校验并拒绝除零。`jd_self_operated_price` 不是计算字段：它是京东自营商品当前活动到手价，不含国补价。`reference_url` 优先同款京东自营旗舰店链接；无同款旗舰店时使用同款京东自营商品链接。

## 前后端计算职责

前端可用当前表单数据预览并提交派生字段，改善即时体验。后端是最终可信计算边界：保存时必须按 `category_id` 查询正式类目扣点率，以 `Decimal` 重算所有冻结公式，并校验前端提交值。一致才可保存；不一致必须拒绝或返回明确 validation error，绝不可无条件保存前端金额或毛利结果。

