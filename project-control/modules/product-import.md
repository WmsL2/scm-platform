# 商品大表导入

状态：NOT_STARTED
Owner：TBD
Last Updated：2026-09-09

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
- 不创建供应商；只匹配已有 Supplier Master；
- Excel 供应商原值保留为 `supplier_name_raw`；按批次和标准化名称产生一次 Match Decision；
- 自动唯一匹配；歧义、未匹配和无效候选须人工解析；
- Confirm 前全部供应商解析完成且重新验证仍有效；正式保存 `source_supplier_id`；
- 不自动创建供应商产品报价；
- Import表只做Staging；
- 确认后写正式 `scm_product`。
- 类目、商品字段与价格规则以 `docs/data-gates/` 冻结文档为准；导入先执行模板、字段、字典及重复/冲突校验，再错误预览与人工确认；错误行不得静默入库。
