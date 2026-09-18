# ADR-0026：商品主数据与类目维表脱钩

状态：ACCEPTED  
日期：2026-09-18

## 背景

商品大表已经提供每条正式商品的一级、二级、三级类目。业务要求商品可在 Excel 导入和手工编辑
中直接维护这些值，不能因为 `scm_category` 中不存在、停用或存在重复路径而阻止商品入库。

## 决策

- Migration `20260918_0032` 删除 `scm_product.category_id`、`scm_product_import_row.category_id`
  及其外键和索引；保留 `scm_category` 表及其类目管理功能。
- 正式 Product 的三级类目由 `category_level1_name`、`category_level2_name`、
  `category_level3_name` 三个文本字段承载，不再写入或查询 Category ID。
- 43 列商品大表的三级类目均为必填文本；预览校验空值，但不再校验 Category 存在、启用状态或
  路径唯一性。Confirm 直接保存这三个文本值。
- 手工编辑同样要求三个层级均非空。编辑页面从现有 Product Master 取得联动候选，同时允许输入
  新文本，输入值不创建或修改类目维表记录。
- Product List 的候选与筛选继续仅基于正式 Product 的路径；类别管理的 CRUD 不再受 Product
  引用保护。投标需求行自己的可选 `category_id` 不受本 ADR 影响。

## 结果

商品导入与编辑不依赖类目主数据准备。类目管理暂时作为独立的维护模块保留；若未来重新需要受控
关联、扣点继承或树形主数据，必须新增 ADR 和不可逆 Migration，不能复用已删除的字段。

## Supersedes

本 ADR 替代 ADR-0018 的 Product Import 绑定、回填与 Confirm 重校验规则，并修正 ADR-0025
中“类目维表继续负责商品编辑和导入受控关联”的陈述。ADR-0025 关于 Product Master 作为筛选
候选来源的决策继续有效。
