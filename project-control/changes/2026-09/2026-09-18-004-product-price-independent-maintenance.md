# 2026-09-18-004 Product Price Independent Maintenance

## Scope

成本价仍为大于零的必填金额，但成本价、价格、利润和比例不再由公式联动。

## Delivered

- 成本价快捷更新仅保存成本价和审计字段，不读取类目或其他价格作为计算输入。
- 商品编辑页保留各价格字段的独立编辑能力，并明确成本价修改不影响其他价格。
- 固定商品大表导入与同键重新导入继续以 Excel 值逐列覆盖。

## Verification

- Product API 回归覆盖成本价更新后其他价格、比例与扣点字段保持原值。
- Alembic Revision：无。
