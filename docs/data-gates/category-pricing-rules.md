# Category and Pricing Rules / 类目与价格规则门禁

状态：PARTIALLY SUPERSEDED BY ADR-0010 / ADR-0024 / ADR-0026
范围：类目来源、扣点规则、价格公式与计算责任；本文件不创建 Category 或 Product Schema。

> ADR-0026 已取消 Product 与 Category 的关联：Excel 一级、二级、三级类目作为 Product 自有必填文本直接保存，Confirm 不再写入 `category_id` 或校验 Category。ADR-0024 冻结价格独立维护：固定大表导入和单独成本价更新均不按类目扣点或公式重算价格、毛利、折扣率和价格虚高比例。

## 类目来源与扣点

真实来源为“商城三级品类维表数据.xlsx”与“工业品产品线.xlsx”。商城三级品类维表包含一级/二级/三级类目 ID 与名称、有效标记、上下柜标记、主营事业部。

- 商城三级类目优先保留来源三级类目 ID，作为 External Category ID。
- 工业品产品线若不存在稳定来源 ID，正式表使用系统生成内部 id；导入前对完全重复路径去重。
- 正式实现不得依赖 Excel 单元格颜色；蓝色仅是来源中的业务规则标记。
- 商城表中标蓝三级类目 `deduction_rate = 0.0500`，其他三级类目 `deduction_rate = 0.0800`。
- 工业品类目未明确标记为 5% 时，当前默认 `deduction_rate = 0.0800`。
- 扣点率必须通过正式 Category Table 数据查询取得，禁止在 Product/Pricing Python 中以类目 `if/else` 写死。

该概念关系不再适用于 Product Master。`scm_category.deduction_rate` 仅属于独立类目管理数据，不能作为商品价格或导入的前置规则。

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

前端和后端将每个价格、利润和比例字段作为独立正式值保存，不计算其相互关系，也不因类目扣点变化覆盖已有字段。金额及比例仍使用 Decimal，并接受各字段既有范围和精度校验。
