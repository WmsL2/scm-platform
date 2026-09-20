# Change Record: Product Import Nullable Numeric Fields

Date: 2026-09-20  
Module: catalog / product-import / matching

## Delivered

- `scm_product.cost_price` 改为 `DECIMAL(65,30) NULL`（Revision `20260920_0035`）；降级前会检查并拒绝存在 NULL 成本价的数据库。
- 43 列导入的正式数值字段统一容错：非数值、非有限值、空值和无效公式结果标准化为 `NULL`，不再产生单独的数值类型行错误。
- 同键重新导入会用 `NULL` 覆盖旧数值；成本价、列表/详情响应、匹配候选与价格快照均支持空值。
- 专用成本价更新 API 仍要求有效正数。

## Verification

相关 catalog、schema 与 matching 测试覆盖可空成本价、非数值、百分比、整数及更新覆盖行为。
