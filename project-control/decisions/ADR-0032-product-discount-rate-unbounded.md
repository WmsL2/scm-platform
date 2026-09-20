# ADR-0032：商品折扣率取消业务范围限制

状态：ACCEPTED  
日期：2026-09-20

## 决策

`scm_product.discount_rate` 只要求为合法有限 `DECIMAL(9,4)`，不设置 `0..1` 的业务范围限制。负值及大于 `1` 的值均可保存；前端仍以百分数输入和显示，数据库继续保存比例值。

Product Import 保持非数值和公式错误标准化为 `NULL`、公式 cached result 四位安全标准化的现有规则。好评率 `positive_rating` 的 `0..1` 约束、Category `deduction_rate` 的 `0..1` 约束均不改变。

## 替代

本 ADR 仅替代 ADR-0021 中折扣率与好评率共同表述的折扣率范围语义；ADR-0021 对好评率、模板和其他字段的决策继续有效。
