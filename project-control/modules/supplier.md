# 供应商

状态：DELETE_IMPORT_IMPLEMENTED_PENDING_MERGE
Owner：人员 A（Backend）/ 人员 B（Frontend）
Last Updated：2026-09-07

## Database
- [x] Revision `20260907_0004`：`scm_supplier`、联系人、资质关系表、合作状态历史表
- [x] Revision `20260908_0005`：逻辑删除审计列、Excel 导入批次与行暂存表
- [x] `supplier_code` 使用 `sys_biz_sequence.SUPPLIER`，数据库全局 UNIQUE

## Backend
- [x] 创建、编辑、详情、分页列表 API
- [x] DRAFT → PENDING → ARCHIVED；NORMAL → STOPPED / BLACKLIST 状态机
- [x] 创建/编辑/归档 Actor 与时间审计；停用/拉黑写合作状态历史
- [x] 逻辑删除 API：保留数据库记录，正常查询过滤 `is_deleted = true`
- [x] Excel 模板下载、上传校验、错误预览、上传者确认后入库

## Frontend
- [x] 供应商列表：真实分页、关键字/双状态筛选、详情跳转
- [x] 新增、详情、编辑：真实 Supplier API 调用与错误反馈
- [x] 多联系人表单：符合 `contacts` 请求契约；联系人可空且每条至少姓名或电话
- [x] 提交归档、归档、停用、黑名单：按实时权限和状态机显示，停用/黑名单收集原因
- [x] 按权限显示删除按钮；下载模板、上传预览、错误行和确认导入流程

## Permissions
- [x] `supplier:list/detail/create/update/submit/archive/stop/blacklist/delete` 已入权限目录并由后端强制校验

## Tests
- [x] MySQL Schema、API 生命周期、401/403、状态机、状态历史覆盖
- [x] 前端 Supplier API 路径、请求体、字段规范化、路由权限单元测试
- [x] 删除权限、逻辑删除保留、Excel 模板/预览/错误行/确认导入 MySQL 集成测试

## Known Issues
- 资质业务字段仍未确认；当前 `scm_supplier_qualification` 只保留已冻结的关系、逻辑删除和审计列，未暴露资质写入 API。
- 联系人字段可空，但一条联系人记录至少要有姓名或电话；`contacts: []` 可用于编辑时清空联系人。
- Migration 仅创建权限目录，不分配用户角色；本机浏览器验收需要使用已经拥有 Supplier 权限的账号。
- `supplier:delete` 仅写入权限目录；管理员用户/角色/权限分配页面由独立 Account 分支实现。未分配该权限时前端不显示删除按钮，后端仍返回 403。
- 导入文件只接受下载模板对应的 `.xlsx`，最多 5 MB、1,000 条数据行；未确认字段、手机号格式验证和来源旧编码均不导入。

## Next Step
为 `supplier:delete` 分配权限后完成浏览器验收，并创建 PR 合并 `fix/supplier-delete-import`；不要新增或猜测未确认供应商字段。

## Design Freeze

- [x] 领域边界、supplier_id 关系原则、supplier_code 规则
- [x] archive_status / cooperation_status 状态机
- [x] 删除策略、审计 Actor、API/权限/页面设计
- [x] 真实供应商字段资料与字段字典
- [x] `supplier_code` 系统生成、全局唯一、不可修改及不回收
- [x] 联系人及联系电话/手机号非必填（nullable；前端不设 required）
- [x] 现有供应商首次导入默认 `ARCHIVED + NORMAL`

## Current Gate

删除与 Excel 导入补丁已在 `fix/supplier-delete-import` 实现，待 PR/Merge；资质业务字段仍需后续资料确认，模块整体不标为 COMPLETED。未确认字段不得自行加入。
