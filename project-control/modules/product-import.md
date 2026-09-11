# 商品大表导入

状态：IMPLEMENTED / PARTIAL_CONFIRM_AND_TEMPLATE_DOWNLOAD
Owner：feat/product-import-partial-confirm-template-download
Last Updated：2026-09-11

## Database
- [x] `20260910_0013` 创建 `scm_product_import_task`、`scm_product_import_row`、`scm_product_import_supplier_match`
- [x] `20260911_0022` 为 Task 增加 `imported_rows`，为 Staging 行增加导入状态与操作审计字段
- [x] 原始 Excel 行和 `supplier_name_raw` 仅保留在 Staging；正式 `scm_product` 不增加供应商名称字段

## Backend
- [x] 严格校验批准的 32 列模板；类目和价格直接按 Excel 正式值保存，不预加载类目、不解析类目、不重算价格
- [x] 提取 WPS/Excel `DISPIMG` 内嵌媒体并保存到相对本地目录；正式 Product 仅保存站内相对图片引用
- [x] 供应商仅按冻结的标准化精确匹配；支持从当前有效 Supplier Master 手动解析
- [x] `POST /api/v1/products/imports/preview`、`GET /api/v1/products/imports/{task_id}`、`GET /api/v1/products/imports/supplier-candidates`、`POST /api/v1/products/imports/{task_id}/supplier-matches/{match_id}/resolve`、`POST /api/v1/products/imports/{task_id}/confirm`
- [x] Confirm 锁定任务并重新校验有效来源供应商；当前通过且尚未导入的行作为一次单事务写入 `scm_product`
- [x] `GET /api/v1/products/imports/template` 下载批准的原始 32 列模板
- [x] 同来源供应商 + SKU 命中停用 Product 时按行报错并阻止 Confirm；不隐式恢复或覆盖，永久删除后才可作为新商品导入

## Frontend
- [x] 商品主数据页提供模板下载、Excel 上传、通过/不通过/已导入行预览筛选、供应商解析和“导入通过行”入口

## Permissions
- [x] `product:import`
- [x] `product:import:resolve`

## Tests
- [x] API 集成测试覆盖未匹配预览、精确匹配和 Confirm 写入 `source_supplier_id`
- [x] 全量后端测试、前端类型检查、单元测试与构建已执行

## Known Issues
- Category Source Loader 不是商品大表导入前置条件；固定模板中的三级类目直接保存到 Product 的原文字段。
- 2026-09-10 对用户提供的 50 行模板进行了事务回滚预检：34 行通过，16 行因供应商为空或未解析而未通过；预检未保留任何暂存或正式数据。
- 旧的预览任务不会回填图片；重新上传后才会按 `20260910_0015` 提取并保存图片。未 Confirm 的预览任务产生的本地媒体后续需要独立的清理策略。

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
- 三级类目和价格字段是固定商品大表的已确认正式值，直接保存；导入先执行模板、必要字段/数值、供应商及重复/冲突校验，再错误预览与人工确认；错误行不得静默入库。
