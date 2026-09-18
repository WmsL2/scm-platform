# Product Master Field Dictionary / 商品主数据字段门禁

状态：FROZEN — `PRODUCT_MASTER_2026_43_COLUMNS`
Last Updated：2026-09-17

## 主数据边界

- 整理后的商品大表一行等于 `scm_product` 一条正式商品；系统 UUID `id` 是主键。
- `source_supplier_id + sku` 是数据库防重业务键，也是重新导入定位键；供应商和 SKU 必填且创建后不可修改。
- 供应商名称只在 Staging 中用于匹配现有 `ARCHIVED + NORMAL + not deleted` Supplier；导入不创建供应商。
- 一级、二级、三级类目是正式 Product 的必填文本；不关联、创建或校验 `MALL_LEVEL3` Category。
- `cost_price` 必填且大于 0。模板中的金额、毛利和比例均作为正式值直接保存，导入不调用 Pricing Service。
- 同键重新导入覆盖其余 41 个模板字段；空单元格清空旧值。若图片替换或清空，数据库事务成功后删除旧本地图片。
- 单独的“修改成本价”操作仅更新成本价；价格、利润和比例均是独立正式值，不自动重算。

## 2026 正式 43 列模板

列顺序必须完全一致；除供应商、SKU、成本价和三级类目绑定外，新增字段均允许为空。

| # | Excel 表头 | 正式字段 / 处理目标 | MySQL 类型 | 规则 |
|---:|---|---|---|---|
| 1 | 所属公司 | `company_name` | `VARCHAR(255)` | 普通文本 |
| 2 | 上架日期 | `listed_at` | `DATE` | 可空 |
| 3 | 品牌 | `brand` | `VARCHAR(128)` | 非唯一 |
| 4 | 图片 | `image_reference` | `VARCHAR(2048)` | 本地媒体相对引用或来源 URL |
| 5 | 型号 | `model` | `VARCHAR(255)` | 非唯一 |
| 6 | sku | `sku` | `VARCHAR(255)` | 必填；与供应商组成 UNIQUE；不可修改 |
| 7 | 商品名称 | `product_name` | `VARCHAR(512)` | 非唯一 |
| 8 | 一级类目 | `category_level1_name` | `VARCHAR(255)` | 必填文本 |
| 9 | 二级类目 | `category_level2_name` | `VARCHAR(255)` | 必填文本 |
| 10 | 三级类目 | `category_level3_name` | `VARCHAR(255)` | 必填文本 |
| 11 | 货号 | `item_number` | `VARCHAR(255)` | 非唯一 |
| 12 | 链接 | `jd_same_product_url` | `VARCHAR(2048)` | 普通链接文本 |
| 13 | 成本价 | `cost_price` | `DECIMAL(65,30)` | 必填且大于 0；保留 Excel 底层原值，不按显示格式四舍五入 |
| 14 | 市场价 | `market_price` | `DECIMAL(65,30)` | 直接保存原值 |
| 15 | 京东价 | `jd_price` | `DECIMAL(65,30)` | 直接保存原值 |
| 16 | 协议价 | `agreement_price` | `DECIMAL(65,30)` | 直接保存原值 |
| 17 | 协议价采购价 | `agreement_purchase_price` | `DECIMAL(65,30)` | 直接保存原值 |
| 18 | 利润 | `profit` | `DECIMAL(18,4)` | 金额；直接保存，不接受 `%` |
| 19 | 京东价毛利（30-50） | `jd_margin` | `DECIMAL(9,4)` | 比率；支持 `0.95` / `95%` |
| 20 | 扣点复核 | `deduction_review` | `DECIMAL(9,4)` | 原“毛利复核”；支持百分比文本 |
| 21 | 毛利率 | `gross_margin` | `DECIMAL(9,4)` | 原“众诚毛利”；支持百分比文本 |
| 22 | 采销员 | `purchasing_agent` | `VARCHAR(128)` | 普通文本，不关联系统用户 |
| 23 | 供应商 | Staging `supplier_name_raw` / 正式 `source_supplier_id` | `VARCHAR(255)` / `CHAR(36)` | 必填；已有合格 Supplier；不可修改 |
| 24 | 69码 | `barcode_text` | `VARCHAR(255)` | 原样文本，不限定纯数字 |
| 25 | 3c编码 | `certification_3c_code` | `VARCHAR(255)` | 单个文本编码 |
| 26 | 产品规格 | `product_specification` | `TEXT` | 原样文本 |
| 27 | 卖点 | `selling_points` | `TEXT` | 原样文本 |
| 28 | 包装清单 | `packaging_list` | `TEXT` | 原样文本 |
| 29 | 质保期 | `warranty_period` | `VARCHAR(255)` | 自由文本 |
| 30 | 限售区域 | `restricted_regions` | `TEXT` | 原样文本 |
| 31 | 京东自营前台价 | `jd_self_operated_price` | `DECIMAL(65,30)` | 直接保存原值 |
| 32 | 自营旗舰店/官方旗舰店 | `storefront_type` | `VARCHAR(64)` | 原样文本 |
| 33 | 参考链接 | `reference_url` | `VARCHAR(2048)` | 普通链接文本 |
| 34 | 销量 | `sales_volume` | `BIGINT` | 可空；整数且大于等于 0 |
| 35 | 好评率 | `positive_rating` | `DECIMAL(9,4)` | `0..1`；支持 `0.95` / `95%`，拒绝裸数字 `95` |
| 36 | 折扣率 | `discount_rate` | `DECIMAL(9,4)` | `0..1`；支持 `0.95` / `95%`，拒绝裸数字 `95` |
| 37 | 价格虚高比例 | `price_inflation_rate` | `DECIMAL(9,4)` | 原“价格虚高比例（30%)”；支持 `0.4625` / `46.25%` |
| 38 | 税收编码 | `tax_code` | `VARCHAR(255)` | 普通文本 |
| 39 | 开票名称 | `invoice_name` | `VARCHAR(512)` | 普通文本 |
| 40 | 税收分类 | `tax_category` | `VARCHAR(255)` | 普通文本 |
| 41 | 发货快递 | `shipping_courier` | `VARCHAR(255)` | 普通文本 |
| 42 | 售后政策 | `after_sales_policy` | `TEXT` | 原样文本 |
| 43 | 备注 | `remark` | `TEXT` | 普通业务文本 |

金额与比率全部使用 Decimal 语义，不使用 Float。正式模板位于
`apps/api-server/app/modules/catalog/resources/product-master-template.xlsx`。

## 查询与页面规则

- 所属公司、采销员、品牌和供应商名称使用包含匹配。
- 类目使用三个独立、可搜索且可多选的下拉框：一级、二级、三级均可直接选择。首次进入商品页不加载完整类目表；用户聚焦或搜索时，`GET /api/v1/products/category-filter-options` 按层级每批最多返回 50 条从当前 Product Master 路径去重的选项，并以 `offset` 与 `has_more` 支持下拉滚动续载。更换搜索词会重置结果集。直接选择三级时，所属一级和二级自动回显；直接选择二级时，所属一级自动回显。前端仅提交用户的直接选择；后端按一级名称、一级/二级路径或完整三级路径组成 OR 条件，自动回显的父级不重复收窄结果。
- 成本价、协议价、折扣率和销量使用包含边界的最小值/最大值筛选；页面折扣率输入 `80` 表示 `0.8`。
- 综合搜索覆盖商品名、品牌、型号、SKU、货号、69码、规格、卖点、三级类目路径、所属公司、采销员和供应商名称；所有筛选条件按 AND 组合。
- 列表默认显示核心列，并允许用户自定义显示列；设置保存在浏览器本地。详情与编辑展示全部业务字段。
- 普通编辑禁止修改供应商和 SKU；图片通过受控上传或清除操作维护，禁止手填服务器路径。

## 导入边界

`标准商品大表 → 严格表头校验 → 字段/字典/重复校验 → 错误预览 → 人工确认 → scm_product`

禁止 AI 猜表头、自动创建 Supplier、执行任意 SQL、静默写入错误行或创建独立 Supplier Product Quote。
