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

`GET /api/v1/products` 支持综合关键字，所属公司/采销员/品牌/供应商名称包含查询，多选分类筛选，成本价/协议价/折扣率/销量闭区间，以及生命周期状态；不同业务条件按 AND 组合。页面分类筛选支持直接搜索并多选一级、二级或三级类目；首次进入不下载完整类目表，用户聚焦或输入关键词时才调用每批 50 条的类目选项接口。下拉框滚动到底会继续加载下一批；更换搜索词则重新从首批加载。任一直接选项以其层级和受控类目 ID 提交，多个已选分类按 OR 查询，父级仅用于同步显示。折扣率输入按百分数换算。

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

商品大表导入的成本价进入正式 Product。供应商给出新报价时，Product Backend 直接更新目标 Product 的 `cost_price`；成本价必须大于零，但不自动计算或覆盖其他价格、利润和比例，既有 `updated_by`、`updated_at` 记录更新审计。

依据 ADR-0024，**固定商品大表导入和手工维护均不调用 Pricing Service**：Excel 的市场价、京东价、协议价、协议价采购价、利润、毛利、折扣率和价格虚高比例均作为已确认正式值直接保存；单独“修改当前成本价”也只改成本价。

## 受控类目绑定

依据 ADR-0018，固定商品大表的一级、二级、三级类目文本只用于精确查询有效的商城三级 `scm_category`。只有唯一匹配时，Confirm 才会把该记录的 `id` 写入 `scm_product.category_id`，并由该记录写入三级类目路径；无匹配、停用或不唯一时，该行不通过且不入库。ADR-0010 关于价格直接保存的规则保持不变。

## 商品图片本地保存

预览只检测固定大表的 WPS/Excel `DISPIMG` 图片，并在有公式图片时受控保留临时源 Excel；预览不提取或保存商品图片。Confirm 时仅当前实际写入正式 Product 的通过行才从临时源文件提取媒体，保存到项目相对目录 `local-data/files/product-images/<import-task-id>/`。实际媒体文件受 `.gitignore` 隔离；数据库不保存本机绝对路径，只保存形如 `local-media/product-images/...` 的站内相对引用。后端通过 `/local-media/` 提供该本地开发媒体。

无法从工作簿找到对应内嵌图片时不阻断其他业务校验；正式 Product 的图片引用为空。非公式图片列仍按原始 URL/文本保存。重新导入替换或清空图片时，先成功提交 Product 更新事务，再删除被替代的旧本地图片。全量 Confirm 后临时源 Excel 立即删除；每次新预览会将超过 `PRODUCT_IMPORT_UNCONFIRMED_RETENTION_DAYS`（默认 7 天）的未完成或部分确认任务标记为 `EXPIRED`，仅删除其临时源文件与未导入行媒体。普通编辑使用 `POST /api/v1/products/{product_id}/image` 上传图片、`DELETE /api/v1/products/{product_id}/image` 清除图片，均要求 `product:update`。

## 大文件导入边界

商品导入默认支持最大 **1GB** 的 `.xlsx` 文件和 **100,000** 条数据行，分别可通过
`PRODUCT_IMPORT_MAX_FILE_MB`、`PRODUCT_IMPORT_MAX_ROWS` 调整。上传按 1MB 分块写入临时文件，
解析使用 `openpyxl` 的只读文件路径；因此 500MB 级商品大表不会因后端的整文件内存读取而被
25MB 旧限制拦截。浏览器预览请求超时为 15 分钟，仍应根据网络、服务器 CPU、磁盘和数据库容量
合理设置部署环境的反向代理上传大小及超时。

`scm_product.source_supplier_id` 表示商品大表该行的**来源供应商**，不是当前报价供应商，也不是唯一供应商。成本价更新不自动新建报价关联或历史记录。

## 来源供应商解析

Excel“供应商”原值只写入 Staging 的 `supplier_name_raw`，用于审计、排障和说明匹配原因；它不是业务外键，匹配成功后也不得删除。正式业务关联始终使用 `source_supplier_id -> scm_supplier.id`，本轮不增加 `source_supplier_name` 或 `supplier_name_snapshot`。

自动匹配仅可使用 `normalize_supplier_name()`：Unicode NFKC、去除首尾空白、将连续空白压缩为一个普通空格。不得删除公司后缀或地区等词语，不得缩写、模糊匹配或由 AI 自动绑定。标准化 Excel 名称与标准化 `scm_supplier.supplier_name` 相等且仅有一个有效候选时，决策为 `MATCHED` / `NAME_EXACT`。

有效候选必须同时为 `ARCHIVED`、`NORMAL`、未逻辑删除。多个有效候选为 `AMBIGUOUS`；没有同名供应商为 `UNMATCHED`；存在同名但均不符合有效条件为 `INELIGIBLE`。后三者必须由用户从当前有效 Supplier Master 中人工选择（`MANUAL`），或先在 Supplier Master 处理后重试；不得在导入页面创建、归档或恢复供应商，也不得创建独立报价记录。

当前实现的 Import Task 状态为 `VALIDATED`、`NEEDS_RESOLUTION`、`READY_TO_CONFIRM`、`PARTIALLY_CONFIRMED`、`CONFIRMED`、`EXPIRED`。每个未处理行另记录 `CREATE` 或 `UPDATE`；`UPDATE` 保留变更字段列表，确认后仍可显示“已更新”。Confirm 对当前所有通过新增行和更新行保持单事务原子性：重新校验必要字段、Match Decision 和每个 `matched_supplier_id` 仍为有效候选后，才提取该批行的图片，创建新 Product 或更新锁定的正常同键 Product。更新保留 ID、创建审计、生命周期状态及供应商 + SKU 键；其余 41 个模板字段按 Excel 覆盖，空单元格清空，价格不重算。任一拟导入行失败不得让本次其他通过行部分写入；不通过行保留在 Staging，绝不入库。

已实现 API：`GET /api/v1/products/imports/template`、`POST /api/v1/products/imports/preview`、`GET /api/v1/products/imports/{task_id}`、`GET /api/v1/products/imports/supplier-candidates`、`POST /api/v1/products/imports/{task_id}/supplier-matches/{match_id}/resolve`、`POST /api/v1/products/imports/{task_id}/confirm`。模板下载与其他导入 API 均要求 `product:import`；人工解析请求只提交 `{ "supplier_id": "<UUID>" }`；Backend 必须再次验证该 UUID 当前有效，前端不得把 supplier_name 作为正式选择结果。
