# 供应商

状态：FIELD_FREEZE_READY_FOR_SCHEMA_DESIGN
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
字段门禁已解除，可在独立 `feat/supplier` 分支进行 Supplier Master Schema Design；Database / Backend / Frontend 仍均未实施。

## Design Freeze

- [x] 领域边界、supplier_id 关系原则、supplier_code 规则
- [x] archive_status / cooperation_status 状态机
- [x] 删除策略、审计 Actor、API/权限/页面设计
- [x] 真实供应商字段资料与字段字典
- [x] `supplier_code` 系统生成、全局唯一、不可修改及不回收
- [x] 联系人及联系电话/手机号非必填（nullable；前端不设 required）
- [x] 现有供应商首次导入默认 `ARCHIVED + NORMAL`

## Current Gate

`FIELD_FREEZE_READY_FOR_SCHEMA_DESIGN`：已确认来源字段与系统字段边界，未确认字段不得自行加入。Supplier 的 Database、Backend、Frontend、Permission 与 Tests 尚未开始，禁止将本模块标为 COMPLETED。
