# 商品主数据定义 / Product Master Data

状态：ACCEPTED
版本：V1.3.2

## 核心定义

公司“商品大表”已经是整理完成的正式具体商品信息。

> **大表一行 = 一条具体正式商品。**

## 导入链路

```text
Excel
 -> 模板校验
 -> 行/字段校验
 -> Import Staging
 -> 错误/冲突预览
 -> 人工确认
 -> scm_product
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

`scm_import_task`
`scm_import_row`
`scm_import_row_error`

只是导入过程，不是正式商品库。

## SPU/SKU

一期不强制 SPU/SKU。

如果未来业务明确需要多规格主体层，再通过新 ADR 扩展。

## 最终字段

必须以真实大表模板逐列冻结。

当前不得凭经验自行定义商品最终字段。

## 唯一键

尚未冻结。

必须在读取真实大表后确认。

禁止自行假设型号或品牌+型号唯一。

## 产品报价

`scm_product` 与 `scm_supplier_product_quote` 是独立数据域。

报价通过 `product_id` 与正式商品建立关联。
