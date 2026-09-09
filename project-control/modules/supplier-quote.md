# 供应商产品报价（已取消）

状态：CANCELLED / SUPERSEDED_BY_ADR-0009
Owner：TBD
Last Updated：2026-09-09

## Database
- [x] 不创建 `scm_supplier_product_quote`

## Backend
- [x] 不创建独立 Quote API、Service 或 Repository

## Frontend
- [x] 不创建独立报价列表、详情、历史或比价页面

## Permissions
- [x] 不新增 Quote 权限编码

## Tests
- [x] 不存在独立 Quote 实现，无 Quote 测试范围

## Known Issues
不保留多供应商报价、报价有效期、报价作废或独立报价历史；这些能力如有需要，必须重新经过业务确认和 ADR。

## Next Step
不再安排 Supplier Product Quote Sprint。后续 Product Backend 在目标 `scm_product` 上直接维护 `cost_price`，并调用 Pricing Service 原子重算派生价格。
