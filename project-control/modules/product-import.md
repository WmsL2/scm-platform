# 商品大表导入

状态：IMPLEMENTED / PRODUCT_MASTER_2026_43_COLUMNS
Owner：feat/product-import-safety-concurrency
Last Updated：2026-09-18

## Database
- [x] `20260910_0013` 创建 `scm_product_import_task`、`scm_product_import_row`、`scm_product_import_supplier_match`
- [x] `20260911_0022` 为 Task 增加 `imported_rows`，为 Staging 行增加导入状态与操作审计字段
- [x] `20260918_0033` 为 Staging 行增加标准化正式值及目标 Product 版本快照，不修改正式业务表
- [x] 原始 Excel 行和 `supplier_name_raw` 仅保留在 Staging；正式 `scm_product` 不增加供应商名称字段

## Backend
- [x] 严格校验批准的 43 列 2026 模板；一级、二级、三级类目必须唯一匹配有效商城三级类目，正式 Product 写入受控 `category_id` 与类目路径；价格仍直接按 Excel 正式值保存，不重算价格
- [x] 预览仅检测 WPS/Excel `DISPIMG` 图片并受控保留临时源 Excel；只有 Confirm 的通过行才提取媒体至相对本地目录，正式 Product 仅保存站内相对图片引用
- [x] 含 `DISPIMG` 的预览在写入临时源文件后显式异步加载暂存行和供应商匹配，避免延迟加载触发 `MissingGreenlet` 并造成预览 500
- [x] 供应商仅按冻结的标准化精确匹配；支持从当前有效 Supplier Master 手动解析
- [x] `POST /api/v1/products/imports/preview`、`GET /api/v1/products/imports/{task_id}`、`GET /api/v1/products/imports/supplier-candidates`、`POST /api/v1/products/imports/{task_id}/supplier-matches/{match_id}/resolve`、`POST /api/v1/products/imports/{task_id}/confirm`
- [x] Confirm 锁定任务并重新校验有效来源供应商；当前通过且尚未导入的行作为一次单事务写入 `scm_product`
- [x] `GET /api/v1/products/imports/template` 下载批准的原始 43 列模板
- [x] 同来源供应商 + SKU 命中停用 Product 时按行报错并阻止 Confirm；不隐式恢复或覆盖，永久删除后才可作为新商品导入
- [x] 同来源供应商 + SKU 命中正常 Product 时按行标识为更新，并在 Confirm 保留 ID/创建审计/状态的前提下原子覆盖固定模板字段；记录变更字段供预览和确认后查看
- [x] 供应商与 SKU 在同键更新中不可修改；其余 41 列全部覆盖，空单元格清空旧值，成功提交后删除被替换的旧本地图片
- [x] 比例、金额和销量在预览阶段统一 Decimal/Pydantic 校验；`46.25%` 标准化为 `0.4625`，空值为 `NULL`，非法文本和无缓存公式结果阻止确认
- [x] Confirm 批量锁定有效供应商和正式商品，并以预览时 Product ID / `updated_at` 检测并发创建、更新或删除；冲突返回 409，不静默覆盖
- [x] 工作簿预览与 Confirm 图片提取共用可配置的进程内并发闸门，默认每进程 1 个重任务

## Frontend
- [x] 商品主数据页提供模板下载、Excel 上传、通过/更新/不通过/已处理行预览筛选、供应商解析和“确认新增/更新”入口
- [x] 导入行明细按状态服务端分页，每页 50 行，避免 4,000+ 行一次返回和渲染

## Permissions
- [x] `product:import`
- [x] `product:import:resolve`

## Tests
- [x] API 集成测试覆盖未匹配预览、精确匹配和 Confirm 写入 `source_supplier_id`
- [x] 全量后端测试、前端类型检查、单元测试与构建已执行

## Known Issues
- 商城三级品类维表是当前模板的受控匹配来源。类目无匹配、停用或不唯一时，该行显示明确原因并保留在 Staging，不写入 Product。
- 2026-09-10 对用户提供的 50 行模板进行了事务回滚预检：34 行通过，16 行因供应商为空或未解析而未通过；预检未保留任何暂存或正式数据。
- `20260914_0023` 后，新预览不再生成商品图片文件；预览表显示“确认后保存”。临时源 Excel 在全量 Confirm 后立即删除；每次新预览会清理超过 `PRODUCT_IMPORT_UNCONFIRMED_RETENTION_DAYS`（默认 7 天）的未完成/部分确认任务的源文件和未导入行媒体，过期任务不可继续确认。已导入 Product 的图片绝不属于此清理范围。
- 升级到 `20260918_0033` 前已生成的未确认更新任务没有 Product 版本快照，必须重新上传预览后再确认。

## Next Step
维护/归档有效 Supplier Master，并为 Excel 的空供应商补齐来源供应商后重新上传该固定模板；不可绕过预览直接导入。

## 已冻结业务规则
- 固定标准大表；
- 不做AI字段映射；
- 不创建供应商；只匹配已有 Supplier Master；
- Excel 供应商原值保留为 `supplier_name_raw`；按批次和标准化名称产生一次 Match Decision；
- 自动唯一匹配；歧义、未匹配和无效候选须人工解析；
- Confirm 前每一条拟导入行的供应商必须解析完成且重新验证仍有效；正式保存 `source_supplier_id`；
- 大表 `cost_price` 写入正式 Product 当前成本价；不自动创建独立供应商报价记录；
- Import表只做Staging；
- 通过行确认后写正式 `scm_product`；不通过行保留在 Staging，绝不静默入库；
- 已导入 Staging 行不得再次写入；Task 以 `PARTIALLY_CONFIRMED` 表示尚有未导入行。
- 正常同键 Product 的待处理行是 `UPDATE`，更新后仍以 Staging 行的 `write_action` 与 `changed_fields` 区分“已更新”；同键停用 Product 仍不通过。
- Excel 三级类目文本仅作为受控商城类目的精确查询条件；唯一有效匹配后，正式 Product 从 Category 写入 `category_id` 与完整路径。价格字段仍直接保存；导入先执行模板、类目、必要字段/数值、供应商及重复/冲突校验，再错误预览与人工确认；错误行不得静默入库。
