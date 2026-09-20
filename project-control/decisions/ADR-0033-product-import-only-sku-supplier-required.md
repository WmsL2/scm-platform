# ADR-0033：商品导入仅 SKU 与供应商必填

状态：ACCEPTED
日期：2026-09-20

## Supersedes

本 ADR 仅替代 ADR-0026 中 Product Import 的一级、二级、三级类目必须非空，以及 Product 手工编辑三级类目必须全部非空的规则。ADR-0026 关于 Product 与 Category Master 解耦、不保存 `category_id`、Import 不依赖 Category Master、Product 保存类目文本和 Category Master 独立维护的决定继续有效。

## Context

2026 固定商品模板必须继续保留 43 个固定、完整且有序的表头。此前规则将三级类目视为必填，和商品主数据允许保留不完整来源资料的导入需求不一致。

## Decision

- Excel 单元格值仅 `sku` 与 `供应商` 必填；供应商仍必须解析为有效的 `ARCHIVED + NORMAL + not deleted` Supplier Master。
- 其余 41 列全部可为空，空字符串和纯空白统一标准化为 `NULL`；同供应商 + SKU 重新导入时，`NULL` 覆盖旧值。
- 三个类目文本字段独立可空；不增加父子路径依赖。类目筛选候选按层级只要求该层及必要父层非空。
- 固定 43 个表头、名称和顺序不变。SKU 防重、供应商匹配、图片有效性、日期处理及各非空字段的格式、精度和业务范围规则不变。
- ADR-0030 的可空数值与公式结果安全标准化、ADR-0032 的折扣率无范围限制均保持不变。

## Consequences

最小合法导入行可仅携带有效 SKU 和供应商。Product 手工编辑可以把三级类目显式更新为 `null`。不需要数据库 Migration，因为三个 Product 类目列已为 nullable。
