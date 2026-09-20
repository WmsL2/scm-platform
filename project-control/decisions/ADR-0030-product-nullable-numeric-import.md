# ADR-0030：商品成本价可空与数值导入容错

状态：ACCEPTED  
日期：2026-09-20

## 决策

`scm_product.cost_price` 调整为可空。固定 43 列商品大表导入时，所有映射到正式 Product 的 Decimal 或 Integer 字段均采用统一的容错 Decimal 标准化：空值、非数值文本、非有限数值、公式无可用缓存结果及公式错误均写为 `NULL`，不单独使该行导入失败。可解析的百分比继续按既有百分比规则转换；已经可解析但违反既有范围约束的值仍按原有规则拒绝。

同来源供应商 + SKU 的重新导入也使用标准化后的值，因此当前 Excel 无法解析的数值会以 `NULL` 覆盖旧正式值。

## 边界

- `PATCH /api/v1/products/{id}/cost-price` 的 `ProductCostUpdateRequest` 仍要求提交大于零的有效 Decimal；本 ADR 不改变该专用维护接口。
- 不改变价格精度 `DECIMAL(65,30)`、供应商/SKU、三级类目、图片、匹配算法或 Pricing Service 边界。
- 不使用 `float()` 解析正式金额。

## 替代

本 ADR 替代 ADR-0010 和 ADR-0024 的下列部分；其余历史决策保持有效：

1. `cost_price` 必填的规定；
2. Product Import 对 `cost_price` 非空、必须可解析的规定；
3. Excel 数值字段为非数值时阻止导入/确认的规定。
