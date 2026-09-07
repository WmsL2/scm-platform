# 供应商

状态：BACKEND_MERGED_FRONTEND_REAL_API_IMPLEMENTED
Owner：人员 A（Backend）/ 人员 B（Frontend）
Last Updated：2026-09-07

## Database
- [x] Revision `20260907_0004`：`scm_supplier`、联系人、资质关系表、合作状态历史表
- [x] `supplier_code` 使用 `sys_biz_sequence.SUPPLIER`，数据库全局 UNIQUE

## Backend
- [x] 创建、编辑、详情、分页列表 API
- [x] DRAFT → PENDING → ARCHIVED；NORMAL → STOPPED / BLACKLIST 状态机
- [x] 创建/编辑/归档 Actor 与时间审计；停用/拉黑写合作状态历史

## Frontend
- [x] 供应商列表：真实分页、关键字/双状态筛选、详情跳转
- [x] 新增、详情、编辑：真实 Supplier API 调用与错误反馈
- [x] 多联系人表单：符合 `contacts` 请求契约；联系人可空且每条至少姓名或电话
- [x] 提交归档、归档、停用、黑名单：按实时权限和状态机显示，停用/黑名单收集原因

## Permissions
- [x] `supplier:list/detail/create/update/submit/archive/stop/blacklist` 已入权限目录并由后端强制校验

## Tests
- [x] MySQL Schema、API 生命周期、401/403、状态机、状态历史覆盖
- [x] 前端 Supplier API 路径、请求体、字段规范化、路由权限单元测试

## Known Issues
- 资质业务字段仍未确认；当前 `scm_supplier_qualification` 只保留已冻结的关系、逻辑删除和审计列，未暴露资质写入 API。
- 联系人字段可空，但一条联系人记录至少要有姓名或电话；`contacts: []` 可用于编辑时清空联系人。
- Migration 仅创建权限目录，不分配用户角色；本机浏览器验收需要使用已经拥有 Supplier 权限的账号。

## Next Step
使用具备 Supplier 权限的本机账号完成浏览器验收；不要新增或猜测未确认供应商字段。

## Design Freeze

- [x] 领域边界、supplier_id 关系原则、supplier_code 规则
- [x] archive_status / cooperation_status 状态机
- [x] 删除策略、审计 Actor、API/权限/页面设计
- [x] 真实供应商字段资料与字段字典
- [x] `supplier_code` 系统生成、全局唯一、不可修改及不回收
- [x] 联系人及联系电话/手机号非必填（nullable；前端不设 required）
- [x] 现有供应商首次导入默认 `ARCHIVED + NORMAL`

## Current Gate

Supplier 主数据的后端与前端真实 API 接入均已完成；资质业务字段仍需后续资料确认，模块整体不标为 COMPLETED。未确认字段不得自行加入。
