# Change Record: Product Discount Rate Unbounded

Date: 2026-09-20  
Module: catalog / product-import

## Delivered

- Product `discount_rate` 移除 `0..1` 的业务范围限制，仍保留 `DECIMAL(9,4)` 容量和精度。
- Product 编辑、Excel Import 与列表区间筛选均支持负折扣率和超过 100% 的折扣率。
- 好评率、Category 扣点率、其他比例字段的范围规则保持不变。
- 公式结果的四位精度安全处理及非数值/公式错误写入 `NULL` 规则保持不变；无数据库迁移。
