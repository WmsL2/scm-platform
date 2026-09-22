# 商品大表导入

状态：IMPLEMENTED / PRODUCT_MASTER_2026_43_COLUMNS / FAILED_ROWS_EXPORT
Owner：codex/fix/product-import-immediate-staging-purge
Last Updated：2026-09-22

## Database
- [x] `20260910_0013` 创建 `scm_product_import_task`、`scm_product_import_row`、`scm_product_import_supplier_match`
- [x] `20260911_0022` 为 Task 增加 `imported_rows`，为 Staging 行增加导入状态与操作审计字段
- [x] `20260918_0033` 为 Staging 行增加标准化正式值及目标 Product 版本快照，不修改正式业务表
- [x] `20260918_0034` 将六个正式价格字段扩展为 `DECIMAL(65,30)`，无损保存价格原值
- [x] `20260922_0038` 为过期导入任务清理增加 `status + created_at` 复合索引
- [x] 原始 Excel 行和 `supplier_name_raw` 仅保留在 Staging；正式 `scm_product` 不增加供应商名称字段

## Backend
- [x] 严格校验批准的 43 列 2026 模板及表头顺序；仅 SKU 与供应商单元格必填，其余 41 列（包括三级类目）可为空并直接保存为 `NULL`，不绑定类目维表外键；价格仍直接按 Excel 正式值保存，不重算价格
- [x] 预览校验 WPS/Excel `DISPIMG` 引用和内嵌媒体元数据并临时保存源 Excel；公式引用缺图、类型不支持或单图超限时该行不通过；只有 Confirm 的通过行才逐张流式提取媒体至相对本地目录，正式 Product 仅保存站内相对图片引用
- [x] Confirm 全部成功后立即删除临时源 Excel、导入行、供应商匹配和 Task；关闭预览弹窗会删除该批未完成暂存数据。正式 Product 与正式商品图片不受影响
- [x] 供应商仅按冻结的标准化精确匹配；支持从当前有效 Supplier Master 手动解析
- [x] 全部行供应商为空时也会正常生成预览：供应商匹配集合在持久化前显式初始化为空列表，不触发 AsyncSession 隐式懒加载；空供应商行仍按规则标记为不通过
- [x] `POST /api/v1/products/imports/preview`、`GET /api/v1/products/imports/{task_id}`、`GET /api/v1/products/imports/supplier-candidates`、`POST /api/v1/products/imports/{task_id}/supplier-matches/{match_id}/resolve`、`POST /api/v1/products/imports/{task_id}/confirm`
- [x] Confirm 锁定任务并重新校验有效来源供应商；当前通过且尚未导入的行作为一次单事务写入 `scm_product`
- [x] `GET /api/v1/products/imports/template` 下载批准的原始 43 列模板
- [x] `GET /api/v1/products/imports/{task_id}/failed-rows` 按上传者导出全部未处理的不通过行；直接加载商品主数据下载所用的正式模板并保留表头、字体、颜色、列宽、行高和单元格格式，从第 2 行填入原值；第二工作表记录原 Excel 行号与错误原因，可修正后直接重新上传
- [x] 失败行导出会把公式随紧凑行号平移；对仍保留临时源文件的 `DISPIMG` 工作簿，只复制失败行实际引用的 WPS 内嵌图片，不把整本大表的无关媒体带入导出文件
- [x] 同来源供应商 + SKU 命中停用 Product 时按行报错并阻止 Confirm；不隐式恢复或覆盖，永久删除后才可作为新商品导入
- [x] 同来源供应商 + SKU 命中正常 Product 时按行标识为更新，并在 Confirm 保留 ID/创建审计/状态的前提下原子覆盖固定模板字段；记录变更字段供预览和确认后查看
- [x] 供应商与 SKU 在同键更新中不可修改；其余 41 列全部覆盖，空单元格清空旧值，成功提交后删除被替换的旧本地图片
- [x] 比例、金额和销量在预览阶段统一 Decimal/Pydantic 标准化；可解析比例及公式结果按既有精度规则保存，六个价格字段以 `DECIMAL(65,30)` 保留 Excel 底层原值；空值、非法文本、无缓存公式结果和 `#DIV/0!` 等数值无效值均为 `NULL`，不单独阻止确认（ADR-0030）
- [x] Excel/WPS 公式 cached result 的金额与比例字段在正式写入前按 4 位 `ROUND_HALF_UP` 标准化，避免浮点尾差触发 Pydantic 精度错误；直接输入的高精度价格字段保持原值，后端不重新执行业务公式（2026-09-20-013）。
- [x] 折扣率允许负值及超过 100%，Import 保持数值容错和公式精度保护；好评率仍限制为 0%～100%（ADR-0032）。
- [x] Confirm 批量锁定有效供应商和正式商品，并以预览时 Product ID / `updated_at` 检测并发创建、更新或删除；冲突返回 409，不静默覆盖
- [x] 工作簿预览与 Confirm 图片提取共用可配置的进程内并发闸门，默认每进程 1 个重任务
- [x] Confirm 浏览器请求允许等待 15 分钟；正式 Product 的供应商 + SKU 查询与锁定按稳定顺序每 500 组分批执行，避免 MySQL 超大复合 `IN` 的范围优化内存告警，同时保持事务原子性和并发冲突保护
- [x] Confirm 不再使用 50MB 全工作簿图片累计上限；每次只解码和保存一张图片，浏览器不直接支持的 TIFF/EMF/BMP/WMF 转为 PNG，单图上限由 `PRODUCT_IMPORT_MAX_IMAGE_MB` 配置（默认 64MB）
- [x] 预览与 Confirm 不再清理任何历史 Task，避免加载历史暂存行 JSON；未收到关闭请求的异常遗留任务由业务方手工处理
- [x] Confirm 在锁定 Task 前准备本次图片文件；锁定、重新校验通过后才将图片键写入 Staging 行并写正式 Product，冲突或失败时仅清理本次新建图片，临时源 Excel 的 24 小时保留与成功后删除规则不变

## Frontend
- [x] 商品主数据页可直接 Confirm；关闭预览弹窗会释放该任务的临时 Excel
- [x] 预览存在不通过行时显示“导出不通过数据”按钮，并按失败行数量生成修正工作簿
- [x] 导入行明细按状态服务端分页，每页 50 行，避免 4,000+ 行一次返回和渲染
- [x] 商品上传预览和 Confirm 均接入通用 Excel 导入锁：显示全屏遮罩、阻止站内路由离开，并在刷新或关闭页面时触发浏览器原生提醒；成功、失败和超时均统一解除锁定
- [x] 上传预览与 Confirm 的浏览器请求在导入入口下方及全屏遮罩内显示实时耗时；请求结束后保留分钟秒数，失败同样记录

## Permissions
- [x] `product:import`
- [x] `product:import:resolve`

## Tests
- [x] API 集成测试覆盖未匹配预览、精确匹配和 Confirm 写入 `source_supplier_id`
- [x] API 回归测试覆盖“所有行供应商为空”，要求返回 200 和空 `supplier_matches`，所有行保留“供应商不能为空”错误而不触发 `MissingGreenlet`
- [x] 回归测试覆盖带 WPS `DISPIMG` 的失败行导出、43 列模板、错误说明及导出文件重新预览
- [x] 通用前端单元测试覆盖无 Excel 导入时允许离开、处理中阻止路由及请求浏览器离开提醒
- [x] Repository 回归测试覆盖终态 Task 按 Row、Supplier Match、Task 的外键顺序删除；图片暂存测试覆盖“准备阶段不写回 Staging 行”
- [x] 全量后端测试、前端类型检查、单元测试与构建已执行

## Known Issues
- 三级类目文本来自固定模板并直接保存到 Product；商品导入不再要求匹配类目维表。
- 2026-09-10 对用户提供的 50 行模板进行了事务回滚预检：34 行通过，16 行因供应商为空或未解析而未通过；预检未保留任何暂存或正式数据。
- 临时源 Excel 仅用于当前导入任务：Confirm 全部成功或用户关闭预览后立即删除并删除该批 Staging。浏览器异常关闭、断网或进程中断时不会自动清理，业务方仅可手工清理 `EXPIRED` / `CONFIRMED` 暂存数据。已导入 Product 的图片绝不属于临时文件清理范围。
- 本次图片流式修复不回填历史 Product，也不扫描或改写既有 `image_reference`；须重新上传并 Confirm 才应用新逻辑。
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
- Excel 三级类目文本作为商品主数据直接保存且允许为空，不转换为 Category 外键。导入先执行模板、SKU/供应商、字段自身格式/数值范围、供应商及重复/冲突校验，再错误预览与人工确认；错误行不得静默入库。
