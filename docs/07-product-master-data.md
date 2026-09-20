# 商品主数据定义 / Product Master Data

状态：ACCEPTED
版本：V1.4.0

## 核心定义

公司“商品大表”已经是整理完成的正式具体商品信息。

> **大表一行 = 一条具体正式商品。**

## 导入链路

```text
Supplier Excel -> Supplier Import -> scm_supplier

商品大表 Excel
 -> 分块上传至临时文件（不整文件读入内存）
 -> 模板、字段、数值、供应商校验
 -> Import Staging（保留 `supplier_name_raw`）
 -> Supplier Matching（按批次及标准化供应商名称）
 -> 错误/冲突/供应商解析预览
 -> 通过行人工 Confirm（保留不通过行）
 -> scm_product（保存 `source_supplier_id`）
```

## 正式查询

以下全部查询正式 `scm_product`：

- 商品列表
- 商品详情
- 商品搜索
- AI商品匹配
- 客户报价
- 场景方案
- 商品统计

`GET /api/v1/products` 支持综合关键字，所属公司/采销员/品牌/供应商名称包含查询，多选分类筛选，成本价/协议价/折扣率/销量闭区间，以及生命周期状态；不同业务条件按 AND 组合。页面分类筛选支持直接搜索并多选一级、二级或三级类目；候选项直接由当前可见正式 `scm_product` 的三级路径去重取得，而不是读取完整类目表。首次进入不请求候选，用户聚焦或输入关键词时才调用 `GET /api/v1/products/category-filter-options` 每批 50 条的接口。下拉框滚动到底会继续加载下一批；更换搜索词则重新从首批加载。直接选项使用路径生成的受控 key 提交，多个已选分类按 OR 查询，父级仅用于同步显示。折扣率输入按百分数换算。

## Import 表

`scm_product_import_task`
`scm_product_import_row`
`scm_product_import_supplier_match`

以上已由 Alembic `20260910_0013` 实现；Revision `20260911_0022` 追加 Task 的 `imported_rows`，以及行的 `is_imported`、`imported_by`、`imported_at`。行以 `supplier_match_id` 关联一个导入批次内每个标准化供应商名称的一次匹配决策，而不是重复保存 `matched_supplier_id`。行级错误、警告和源/缓存单元格值随暂存行保存，不另建 `scm_import_row_error`。

只是导入过程，不是正式商品库。

## SPU/SKU

一期不强制 SPU/SKU。

如果未来业务明确需要多规格主体层，再通过新 ADR 扩展。

## 最终字段

真实大表字段边界已在 `docs/data-gates/product-master-field-dictionary.md` 冻结。正式 Schema 设计必须以该字典和真实大表为准，不得凭经验自行增加未知字段。

## 唯一键

系统生成的 `id` 是主键。`source_supplier_id + sku` 是 Product 防重业务键，并由数据库 UNIQUE 强制；两个字段对新导入必填，创建后不能通过重新导入或普通编辑修改。`model`、`product_name`、`brand + model`、货号及源69码文本均不设业务 UNIQUE。

## 商品停用与永久删除

Revision `20260911_0020` 将 Product 生命周期冻结为 `ACTIVE` / `DISABLED`。`POST /api/v1/products/{product_id}/commands/disable` 与 `enable` 均要求 `product:disable`；停用后商品从正常列表、详情、编辑及成本价更新中隐藏，但 Product ID、字段和 `source_supplier_id + sku` 防重业务键继续保留。

`DELETE /api/v1/products/{product_id}` 是永久删除，要求 `product:purge` 和请求体 `{"confirm": true}`，且仅允许删除已停用商品。服务端会在同一事务锁定商品、写入 `scm_product_purge_audit` 的最小审计信息后物理删除；存在数据库受保护关联时返回冲突。永久删除后同键释放，重新导入会创建一条新商品。正常商品的同键 Excel 行依据 ADR-0020 标记为更新并可在 Confirm 覆盖固定模板字段；停用商品的同键 Excel 行仍在预览阶段阻止 Confirm，不恢复也不覆盖既有字段。

## 当前成本价

`scm_product.cost_price` 是具体正式商品的当前成本价，也是业务确认的当前供应商报价。一期不建设 `scm_supplier_product_quote`，不保存独立报价历史、有效期、作废记录或多供应商比价结果。

商品大表导入的成本价进入正式 Product；成本价允许为空，Excel 空值、非数值或无效公式结果会标准化为 `NULL`。供应商给出新报价时，专用 Product Backend 成本价更新接口仍要求提交大于零的有效值；该接口不自动计算或覆盖其他价格、利润和比例，既有 `updated_by`、`updated_at` 记录更新审计。

依据 ADR-0024，**固定商品大表导入和手工维护均不调用 Pricing Service**：Excel 的市场价、京东价、协议价、协议价采购价、利润、毛利、折扣率和价格虚高比例均作为已确认正式值直接保存；单独“修改当前成本价”也只改成本价。

## 商品自有三级类目

依据 ADR-0026，固定商品大表的一级、二级、三级类目是 Product 自身的三个必填文本字段。导入预览只校验三项不得为空；不再查询、创建或绑定 `scm_category`，类目不存在、停用或路径重复均不会阻止入库。手工编辑也必须填写三级路径，可从正式 Product Master 取得联动候选或直接输入新值。类目管理维表继续独立存在。

## 商品图片本地保存

预览校验固定大表的 WPS/Excel `DISPIMG` 引用及内嵌媒体元数据，临时保存源 Excel，但不提取或保存商品图片。Confirm 时仅当前实际写入正式 Product 的通过行才从临时源文件逐张流式解码并保存到项目相对目录 `local-data/files/product-images/<import-task-id>/`。Confirm 成功或用户关闭预览弹窗时立即删除该临时 Excel；异常关闭时按 24 小时兜底过期清理。不再把整批图片读入内存，也不再使用旧的 50MB 全工作簿累计上限。实际媒体文件受 `.gitignore` 隔离；数据库不保存本机绝对路径，只保存形如 `local-media/product-images/...` 的站内相对引用。后端通过 `/local-media/` 提供该本地开发媒体。

图片列为空仍允许导入；但只要存在 `DISPIMG` 公式，其引用的内嵌媒体缺失、类型不支持、单图超过 `PRODUCT_IMPORT_MAX_IMAGE_MB`（默认 64MB）或 Confirm 时无法安全解码，该行就必须失败，不允许静默写成无图商品。PNG/JPEG/GIF/WebP 保持原格式，TIFF/EMF/BMP/WMF 保存前转换为 PNG，确保浏览器可显示。非公式图片列仍按原始 URL/文本保存。重新导入替换或清空图片时，先成功提交 Product 更新事务，再删除被替代的旧本地图片。关闭预览会调用 `POST /api/v1/products/imports/{task_id}/discard` 删除临时源 Excel；未关闭任务以 24 小时为兜底清理边界。普通编辑使用 `POST /api/v1/products/{product_id}/image` 上传图片、`DELETE /api/v1/products/{product_id}/image` 清除图片，均要求 `product:update`。本规则不自动回填或改写历史 Product；历史数据需重新上传并 Confirm 才应用新逻辑。

## 大文件导入边界

商品导入默认支持最大 **1GB** 的 `.xlsx` 文件和 **100,000** 条数据行，分别可通过
`PRODUCT_IMPORT_MAX_FILE_MB`、`PRODUCT_IMPORT_MAX_ROWS` 调整。上传按 1MB 分块写入临时文件，
解析使用 `openpyxl` 的只读文件路径；因此 500MB 级商品大表不会因后端的整文件内存读取而被
25MB 旧限制拦截。浏览器预览请求超时为 15 分钟，仍应根据网络、服务器 CPU、磁盘和数据库容量
合理设置部署环境的反向代理上传大小及超时。

工作簿解析与 Confirm 图片提取共用进程内资源闸门，默认每 API 进程同时执行 1 个重任务，可用
`PRODUCT_IMPORT_MAX_CONCURRENT_WORKBOOKS` 调整。数据库暂存行按 500 条批量写入；行明细使用
`page`、`page_size`（最大 100）和 `row_status=ALL|PASSED|UPDATE|FAILED` 服务端分页，页面默认
每页 50 行。该闸门只限制重型工作簿操作，不阻止商品查询等普通请求；多 Worker 部署时总并发量是
各 Worker 配置之和。

Confirm 的浏览器请求单独允许等待 15 分钟，避免大表后端已完成而浏览器默认 10 秒中止并误报失败。
用于预览和 Confirm 的 `source_supplier_id + sku` 查询按稳定顺序每 500 组分批执行；Confirm 保持同一
事务和相同锁顺序，不因分批而放松并发冲突保护，也不触发 MySQL 的超大复合 `IN (...)` 范围优化内存告警。

所有金额、比例和销量在预览阶段转换并经过 Pydantic/Decimal 校验，标准化结果单独保存在 Staging。
带 `%` 的比例除以 100，例如 `46.25%` 保存为 `0.4625`；不带 `%` 的比例按数据库小数值解释；
空单元格写 `NULL`。`profit` 是金额，不接受 `%`。`5000+` 等非法内容、非有限值和没有缓存计算结果的数值公式均标准化为 `NULL`，不会把原始字符串直接交给 MySQL，也不会仅因此使该行不通过；已可解析但违反既有范围约束的数值仍会被拒绝。

`scm_product.source_supplier_id` 表示商品大表该行的**来源供应商**，不是当前报价供应商，也不是唯一供应商。成本价更新不自动新建报价关联或历史记录。

## 来源供应商解析

Excel“供应商”原值只写入 Staging 的 `supplier_name_raw`，用于审计、排障和说明匹配原因；它不是业务外键，匹配成功后也不得删除。正式业务关联始终使用 `source_supplier_id -> scm_supplier.id`，本轮不增加 `source_supplier_name` 或 `supplier_name_snapshot`。

自动匹配仅可使用 `normalize_supplier_name()`：Unicode NFKC、去除首尾空白、将连续空白压缩为一个普通空格。不得删除公司后缀或地区等词语，不得缩写、模糊匹配或由 AI 自动绑定。标准化 Excel 名称与标准化 `scm_supplier.supplier_name` 相等且仅有一个有效候选时，决策为 `MATCHED` / `NAME_EXACT`。

有效候选必须同时为 `ARCHIVED`、`NORMAL`、未逻辑删除。多个有效候选为 `AMBIGUOUS`；没有同名供应商为 `UNMATCHED`；存在同名但均不符合有效条件为 `INELIGIBLE`。后三者必须由用户从当前有效 Supplier Master 中人工选择（`MANUAL`），或先在 Supplier Master 处理后重试；不得在导入页面创建、归档或恢复供应商，也不得创建独立报价记录。

当前实现的 Import Task 状态为 `VALIDATED`、`NEEDS_RESOLUTION`、`READY_TO_CONFIRM`、`PARTIALLY_CONFIRMED`、`CONFIRMED`、`EXPIRED`。每个未处理行另记录 `CREATE` 或 `UPDATE`；`UPDATE` 保留变更字段列表，确认后仍可显示“已更新”。Confirm 对当前所有通过新增行和更新行保持单事务原子性：重新校验必要字段、Match Decision 和每个 `matched_supplier_id` 仍为有效候选后，才提取该批行的图片，创建新 Product 或更新锁定的正常同键 Product。更新保留 ID、创建审计、生命周期状态及供应商 + SKU 键；其余 41 个模板字段按 Excel 覆盖，空单元格清空，价格不重算。任一拟导入行失败不得让本次其他通过行部分写入；不通过行保留在 Staging，绝不入库。

系统不以文件名或文件哈希判断两个用户是否导入“同一份 Excel”。不同任务命中相同的
`source_supplier_id + sku` 时，Confirm 会锁定对应正式商品并比较预览时的 Product ID / `updated_at`。
预览后若另一任务已创建、更新或删除该商品，当前确认返回 `PRODUCT_IMPORT_STALE_PREVIEW`（409），
要求重新上传预览；数据库 UNIQUE 约束继续兜底创建竞争。因此并发不会静默采用“后确认覆盖先确认”。

已实现 API：`GET /api/v1/products/imports/template`、`POST /api/v1/products/imports/preview`、`GET /api/v1/products/imports/{task_id}`、`GET /api/v1/products/imports/supplier-candidates`、`POST /api/v1/products/imports/{task_id}/supplier-matches/{match_id}/resolve`、`POST /api/v1/products/imports/{task_id}/confirm`。模板下载与其他导入 API 均要求 `product:import`；人工解析请求只提交 `{ "supplier_id": "<UUID>" }`；Backend 必须再次验证该 UUID 当前有效，前端不得把 supplier_name 作为正式选择结果。
