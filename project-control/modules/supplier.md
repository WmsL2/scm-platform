# 供应商

状态：BACKEND_IMPLEMENTED_FRONTEND_PENDING
Owner：人员 A（Backend）
Last Updated：2026-09-07

## Database
- [x] Revision `20260907_0004`：`scm_supplier`、联系人、资质关系表、合作状态历史表
- [x] `supplier_code` 使用 `sys_biz_sequence.SUPPLIER`，数据库全局 UNIQUE

## Backend
- [x] 创建、编辑、详情、分页列表 API
- [x] DRAFT → PENDING → ARCHIVED；NORMAL → STOPPED / BLACKLIST 状态机
- [x] 创建/编辑/归档 Actor 与时间审计；停用/拉黑写合作状态历史

## Frontend
- [ ] 未开始

## Permissions
- [x] `supplier:list/detail/create/update/submit/archive/stop/blacklist` 已入权限目录并由后端强制校验

## Tests
- [x] MySQL Schema、API 生命周期、401/403、状态机、状态历史覆盖

## Known Issues
- 资质业务字段仍未确认；当前 `scm_supplier_qualification` 只保留已冻结的关系、逻辑删除和审计列，未暴露资质写入 API。
- 联系人字段可空，但一条联系人记录至少要有姓名或电话；`contacts: []` 可用于编辑时清空联系人。

## Next Step
由人员 B 在独立前端分支实现供应商列表、新增、详情、编辑及状态操作页面，并接入已冻结 API；不要新增或猜测未确认供应商字段。

## Design Freeze

- [x] 领域边界、supplier_id 关系原则、supplier_code 规则
- [x] archive_status / cooperation_status 状态机
- [x] 删除策略、审计 Actor、API/权限/页面设计
- [x] 真实供应商字段资料与字段字典
- [x] `supplier_code` 系统生成、全局唯一、不可修改及不回收
- [x] 联系人及联系电话/手机号非必填（nullable；前端不设 required）
- [x] 现有供应商首次导入默认 `ARCHIVED + NORMAL`

## Current Gate

后端实施已完成，Supplier 模块整体不能标为 COMPLETED：前端尚未实施，且资质业务字段仍需后续资料确认。未确认字段不得自行加入。
