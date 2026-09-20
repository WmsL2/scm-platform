# Change Record: Product Import Formula-Derived Decimal Tail Precision

Date: 2026-09-20  
Module: catalog / product-import

## Delivered

- 修复 Excel/WPS 公式 cached result 的二进制 Decimal 尾差，不在后端重新执行价格、扣点或利润业务公式。
- 公式派生金额和比例字段按 4 位 `ROUND_HALF_UP` 吸附到正式字段精度；`profit` 直接输入同样按其正式 `DECIMAL(18,4)` 标准化。
- 直接输入的 `DECIMAL(65,30)` 高精度价格不传入 quantum，继续保留有效原始精度。
- 非数值和公式错误写入 `NULL` 的 ADR-0030 行为不变；未新增数据库迁移。

## Verification

- 覆盖公式缓存尾差、General 直接数值、利润五位小数，以及高精度市场价回归。
