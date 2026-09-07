# 商品大表导入

状态：NOT_STARTED
Owner：TBD
Last Updated：2026-09-07

## Database
- [ ] 未开始

## Backend
- [ ] 未开始

## Frontend
- [ ] 未开始

## Permissions
- [ ] 未开始

## Tests
- [ ] 未开始

## Known Issues
无。

## Next Step
等待对应 Sprint。

## 已冻结业务规则
- 固定标准大表；
- 不做AI字段映射；
- 不选择供应商；
- 不自动创建供应商产品报价；
- Import表只做Staging；
- 确认后写正式 `scm_product`。
- 类目、商品字段与价格规则以 `docs/data-gates/` 冻结文档为准；导入先执行模板、字段、字典及重复/冲突校验，再错误预览与人工确认；错误行不得静默入库。
