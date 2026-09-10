# 商品主数据定义 / Product Master Data

状态：ACCEPTED
版本：V1.3.2

## 核心定义

公司“商品大表”已经是整理完成的正式具体商品信息。

> **大表一行 = 一条具体正式商品。**

## 导入链路

```text
Supplier Excel -> Supplier Import -> scm_supplier

商品大表 Excel
 -> 模板、字段、数值、供应商校验
 -> Import Staging（保留 `supplier_name_raw`）
 -> Supplier Matching（按批次及标准化供应商名称）
 -> 错误/冲突/供应商解析预览
 -> 全部解析后人工 Confirm
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

## Import 表

`scm_product_import_task`
`scm_product_import_row`
`scm_product_import_supplier_match`

以上已由 Alembic `20260910_0010` 实现。行以 `supplier_match_id` 关联一个导入批次内每个标准化供应商名称的一次匹配决策，而不是重复保存 `matched_supplier_id`。行级错误、警告和源/缓存单元格值随暂存行保存，不另建 `scm_import_row_error`。

只是导入过程，不是正式商品库。

## SPU/SKU

一期不强制 SPU/SKU。

如果未来业务明确需要多规格主体层，再通过新 ADR 扩展。

## 最终字段

真实大表字段边界已在 `docs/data-gates/product-master-field-dictionary.md` 冻结。正式 Schema 设计必须以该字典和真实大表为准，不得凭经验自行增加未知字段。

## 唯一键

系统生成的 `id` 是主键。`model`、`sku`、`product_name`、`brand + model`、货号及源69码文本均不设业务 UNIQUE；不得自行假设型号或品牌+型号唯一。

## 当前成本价

`scm_product.cost_price` 是具体正式商品的当前成本价，也是业务确认的当前供应商报价。一期不建设 `scm_supplier_product_quote`，不保存独立报价历史、有效期、作废记录或多供应商比价结果。

商品大表导入的成本价进入正式 Product。供应商给出新报价时，后续 Product Backend 直接更新目标 Product 的 `cost_price`，并在同一事务内按 Pricing Service 重新计算和保存派生价格与毛利；既有 `updated_by`、`updated_at` 记录更新审计。

依据 ADR-0010，**固定商品大表导入本身不调用 Pricing Service**：Excel 的市场价、京东价、协议价、协议价采购价、利润、毛利、折扣率和价格虚高比例均作为已确认正式值直接保存。仅单独“更新当前成本价”操作仍须重算，因为该操作不同时提供整行完整价格数据。

## 类目直接保存

依据 ADR-0010，固定商品大表的一级、二级、三级类目直接保存到 `scm_product.category_level1_name`、`category_level2_name`、`category_level3_name`。导入不读取或写入 `scm_category`，也不以类目路径生成 `category_id`；`category_id` 是可空的未来受控类目关联，不是 Confirm 前置条件。

## 商品图片本地保存

固定大表的 WPS/Excel `DISPIMG` 图片会在预览时从工作簿内嵌媒体提取，保存到项目相对目录 `local-data/files/product-images/<import-task-id>/`。实际媒体文件受 `.gitignore` 隔离，其他开发者在自己的项目目录使用相同相对位置即可保存；数据库不保存本机绝对路径，只保存形如 `local-media/product-images/...` 的站内相对引用。后端通过 `/local-media/` 提供该本地开发媒体。

无法从工作簿找到对应内嵌图片时只产生警告，不影响供应商等其他校验；正式 Product 的图片引用为空。非公式图片列仍按原始 URL/文本保存。

`scm_product.source_supplier_id` 表示商品大表该行的**来源供应商**，不是当前报价供应商，也不是唯一供应商。成本价更新不自动新建报价关联或历史记录。

## 来源供应商解析

Excel“供应商”原值只写入 Staging 的 `supplier_name_raw`，用于审计、排障和说明匹配原因；它不是业务外键，匹配成功后也不得删除。正式业务关联始终使用 `source_supplier_id -> scm_supplier.id`，本轮不增加 `source_supplier_name` 或 `supplier_name_snapshot`。

自动匹配仅可使用 `normalize_supplier_name()`：Unicode NFKC、去除首尾空白、将连续空白压缩为一个普通空格。不得删除公司后缀或地区等词语，不得缩写、模糊匹配或由 AI 自动绑定。标准化 Excel 名称与标准化 `scm_supplier.supplier_name` 相等且仅有一个有效候选时，决策为 `MATCHED` / `NAME_EXACT`。

有效候选必须同时为 `ARCHIVED`、`NORMAL`、未逻辑删除。多个有效候选为 `AMBIGUOUS`；没有同名供应商为 `UNMATCHED`；存在同名但均不符合有效条件为 `INELIGIBLE`。后三者必须由用户从当前有效 Supplier Master 中人工选择（`MANUAL`），或先在 Supplier Master 处理后重试；不得在导入页面创建、归档或恢复供应商，也不得创建独立报价记录。

当前实现的 Import Task 状态为 `VALIDATED`、`NEEDS_RESOLUTION`、`READY_TO_CONFIRM`、`CONFIRMED`。Confirm 必须为全批次原子事务：重新校验全部行必要字段和全部 Match Decision 为 `MATCHED`，并重新查询每个 `matched_supplier_id` 仍是有效候选后，才写正式商品并将其作为 `source_supplier_id`。类目和 Excel 价格不再被二次解析或重算。任一供应商/必要字段失败不得部分写入；先前匹配成功后供应商变为 STOPPED、BLACKLIST 或删除也必须使 Confirm 失败。

已实现 API：`POST /api/v1/products/imports/preview`、`GET /api/v1/products/imports/{task_id}`、`GET /api/v1/products/imports/supplier-candidates`、`POST /api/v1/products/imports/{task_id}/supplier-matches/{match_id}/resolve`、`POST /api/v1/products/imports/{task_id}/confirm`。人工解析请求只提交 `{ "supplier_id": "<UUID>" }`；Backend 必须再次验证该 UUID 当前有效，前端不得把 supplier_name 作为正式选择结果。
