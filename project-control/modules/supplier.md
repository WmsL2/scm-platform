# 供应商

状态：DELETE_IMPORT_MERGED / NAME_UNIQUENESS_HARDENED
Owner：人员 A（Backend）/ 人员 B（Frontend）
Last Updated：2026-09-10

## Database
- [x] Revision `20260907_0004`：`scm_supplier`、联系人、资质关系表、合作状态历史表
- [x] Revision `20260908_0005`：逻辑删除审计列、Excel 导入批次与行暂存表
- [x] `supplier_code` 使用 `sys_biz_sequence.SUPPLIER`，数据库全局 UNIQUE
- [x] `supplier_name` 数据库全局 UNIQUE（含逻辑删除记录）；历史重复记录已按每个名称保留最早一条完成数据清理

## Backend
- [x] 创建、编辑、详情、分页列表 API；活跃同名创建/改名返回“该供应商已存在”
- [x] 详情页“相关商品”入口：仅拥有 `product:list` 的用户可进入，跳转后只显示该供应商作为来源供应商的正式商品
- [x] DRAFT → PENDING → ARCHIVED；NORMAL ↔ STOPPED、NORMAL ↔ BLACKLIST 状态机；无 STOPPED ↔ BLACKLIST
- [x] 创建/编辑/归档 Actor 与时间审计；停止/拉黑及恢复/移出黑名单均写合作状态历史和原因
- [x] 逻辑删除 API：保留数据库记录，正常查询过滤 `is_deleted = true`；同名再次创建时复用该历史记录、恢复并覆盖业务数据，编码不变
- [x] Excel 模板下载、上传校验、错误预览；有效文件上传后自动入库，活动同名供应商及 Excel 内重复行会逐行提示
- [x] 导入确认采用原子持久化：锁定并直接读取批次行，Supplier 写入 `flush` 成功且数量一致后才标记 `CONFIRMED`；异常整批回滚

## Frontend
- [x] 供应商列表：真实分页、关键字/双状态筛选、详情跳转
- [x] 新增、详情、编辑：真实 Supplier API 调用与错误反馈
- [x] 多联系人表单：符合 `contacts` 请求契约；联系人可空且每条至少姓名或电话
- [x] 提交归档、归档、停止合作、黑名单、恢复合作、移出黑名单：按实时权限和状态机显示，全部合作状态操作收集原因
- [x] 按权限显示删除按钮；下载模板、上传校验结果；无错误 Excel 自动导入，错误文件保留逐行提示供修正后重传

## Permissions
- [x] `supplier:list/detail/create/update/submit/archive/stop/blacklist/resume/unblacklist/delete` 已入权限目录并由后端强制校验

## Tests
- [x] MySQL Schema、API 生命周期、401/403、状态机、状态历史覆盖
- [x] 前端 Supplier API 路径、请求体、字段规范化、路由权限单元测试
- [x] 删除权限、逻辑删除保留、同名恢复覆盖、名称唯一、Excel 模板/预览/错误行/确认导入 MySQL 集成测试
- [x] Post-merge：Supplier UUID Path Validation（`422` / `VALIDATION_ERROR`）与
  caller-owned transaction rollback 回归覆盖
- [x] Supplier Matching Foundation：空白输入校验、名称标准化、有效候选判断与确定性匹配分类

## Post-Merge Hardening

- Supplier 与 Import Service 使用共享事务作用域；已有 caller-owned transaction
  仅参与，不自行 commit / rollback。
- `supplier_id`（详情、编辑、删除、状态命令）与 Import confirm 的 `batch_id`
  在 Router 边界使用 `uuid.UUID` 验证，非法值不会进入 UUIDChar36 ORM。
- Revision `20260910_0016` 已加入供应商名称全局 UNIQUE；Alembic 链维持单 Head。

## Import Confirmation Integrity

- 确认接口不再将 ORM 关系集合视为导入工作集，而是锁定并直接查询
  `scm_supplier_import_row`。
- 批次头部的 `total_rows`、`valid_rows` 必须与实际锁定行一致；不一致时返回
  `409 SUPPLIER_IMPORT_BATCH_INTEGRITY_ERROR`，批次保持 `VALIDATED`，不会写入任何供应商。
- 所有新增或恢复的 Supplier 均在返回成功前执行 `flush`；只有成功写入的实际数量
  与行数一致时才更新批次为 `CONFIRMED`。
- 已被旧逻辑错误标记为 `CONFIRMED` 的历史批次保持审计记录，不自动重放，以免在
  无法确认最终意图时写入错误或重复数据；需要重新上传原始 Excel。

## Supplier Matching Foundation

- `SupplierCreateRequest` 与 `SupplierUpdateRequest` 对 `supplier_name`、
  `main_brands`、`advantage` 采用相同的本地 Pydantic 校验：去除首尾空白后不得为空；
  联系人空白字段归一为 `None`，但联系人至少仍须保留姓名或电话其中之一。
- `normalize_supplier_name()` 仅执行 Unicode NFKC、首尾空白去除和连续 Unicode
  空白压缩为一个普通空格；不删除公司后缀或地区，也不进行简称、大小写、拼音、模糊或 AI 替换。
- `is_eligible_source_supplier()` 统一要求 `ARCHIVED + NORMAL + not deleted`。
- `classify_supplier_name_match()` 仅基于标准化后严格同名分类为
  `MATCHED/NAME_EXACT`、`AMBIGUOUS`、`UNMATCHED` 或 `INELIGIBLE`；仅唯一有效候选
  才返回其 `supplier_id`。
- 本阶段未新增 Repository 查询、Migration、Product Import 表、API 或 Frontend。
  数据库候选检索将在未来 Product Import 按届时 Schema 决定，不能复用 Supplier 列表的
  `contains` 搜索。

## Known Issues
- 资质业务字段仍未确认；当前 `scm_supplier_qualification` 只保留已冻结的关系、逻辑删除和审计列，未暴露资质写入 API。
- 联系人字段可空，但一条联系人记录至少要有姓名或电话；`contacts: []` 可用于编辑时清空联系人。
- Migration 仅创建权限目录，不分配用户角色；本机浏览器验收需要使用已经拥有 Supplier 权限的账号。
- `supplier:delete` 仅写入权限目录；管理员用户/角色/权限分配页面由独立 Account 分支实现。未分配该权限时前端不显示删除按钮，后端仍返回 403。
- 导入文件只接受下载模板对应的 `.xlsx`，最多 5 MB、1,000 条数据行；未确认字段、手机号格式验证和来源旧编码均不导入。活动供应商重名或 Excel 内重名会阻止整批导入；已逻辑删除的同名供应商可被导入恢复并覆盖。

## Next Step
为 `supplier:delete` 分配权限后完成浏览器验收；不要新增或猜测未确认供应商字段。

## Design Freeze

- [x] 领域边界、supplier_id 关系原则、supplier_code 规则
- [x] archive_status / cooperation_status 状态机
- [x] 删除策略、审计 Actor、API/权限/页面设计
- [x] 真实供应商字段资料与字段字典
- [x] `supplier_code` 系统生成、全局唯一、不可修改及不回收
- [x] 联系人及联系电话/手机号非必填（nullable；前端不设 required）
- [x] 现有供应商首次导入默认 `ARCHIVED + NORMAL`

## Current Gate

Delete & Import 已合入并完成事务/UUID/名称唯一加固；资质业务字段仍需后续资料确认，模块整体不标为 COMPLETED。未确认字段不得自行加入。
