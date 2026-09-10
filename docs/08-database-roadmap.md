# 数据库 Roadmap / Table Scope V1.3.2

注意：

> 本文是按 Sprint 的表范围规划，不是最终 DDL。

商品大表最终字段和 Catalog 表结构必须在真实大表数据字典冻结后确定。

因此本版本**不再提前锁死“44张表”**。

---

# Sprint 0

只建立 Migration 能力和必要技术基线。

不一次性创建业务全表。

---

# Sprint 1：System + Supplier

计划：

- `sys_department`
- `sys_user`
- `sys_role`
- `sys_permission`
- `sys_user_role`
- `sys_role_permission`
- `sys_dict_type`
- `sys_dict_item`
- `sys_config`
- `sys_biz_sequence`
- `sys_file`
- `sys_operation_log`
- `sys_login_log`
- `sys_outbox_event`

Supplier：

- `scm_supplier`
- `scm_supplier_contact`
- `scm_supplier_qualification`
- `scm_supplier_cooperation_record`

---

# Sprint 2：Product Cost Pricing

不创建 `scm_supplier_product_quote` 或任何独立报价历史表。当前成本价和按冻结公式得出的派生价格字段属于后续 `scm_product`；Product Migration 前仍须遵守 Category / Product Schema Gate。

---

# Sprint 3：Product Master（已实现基础查询与成本价维护）

当前存在：

- `scm_product`
- `scm_product.source_supplier_id` FK → `scm_supplier.id`（来源供应商，不是当前报价或唯一供应商）
- `scm_product.category_level1_name`、`category_level2_name`、`category_level3_name`（固定商品大表直接保存的完整类目文字）
- 可空的 `scm_product.category_id`（未来受控类目关联，不是导入前置条件）
- `scm_product.cost_price`（当前成本价；业务确认等同当前供应商报价）
- `scm_category`
- 品牌相关表（如需要）
- 参数扩展相关表（如需要）

是否拆品牌、分类、参数表，必须以真实大表字段和检索需求决定。

当前已实现 Product 列表、详情、成本价更新和商品大表导入。固定商品大表直接保存完整类目和价格值；Category Source Loader 不是 Confirm 前置条件。

明确：

- 不默认创建 `scm_product_sku`
- 不默认创建 `scm_supplier_sku`

---

# Sprint 4：Product Import（已实现）

- `scm_product_import_task`
- `scm_product_import_row`（以 `source_data`、`calculated_data`、`supplier_name_raw`、`image_storage_key` 和行级错误/警告保存 Staging）
- `scm_product_import_supplier_match`（按 import_task_id + supplier_name_normalized 的来源供应商匹配决策）

由 Alembic `20260910_0010` 创建，并由 `20260910_0012` 增加图片暂存键。Import 表只保留导入过程；Confirm 后正式数据写入 `scm_product`，不会新增报价表或把供应商原名称写入 Product。

---

# Sprint 5：Customer / Matching / Quotation

计划：

- `scm_customer`
- `scm_customer_requirement`
- `scm_customer_requirement_item`
- `scm_match_task`
- `scm_match_candidate`
- `scm_sales_quotation`
- `scm_sales_quotation_item`
- `scm_sales_quotation_export`

报价 Item 必须保存快照。

---

# Sprint 6：Solution

计划：

- `scm_solution_template`
- `scm_solution`
- `scm_solution_item`
- `scm_solution_export`

以及 AI 配置如业务确认需要：

- `scm_ai_rule_set`
- `scm_ai_model_config`

---

# 原则

最终 DDL 必须：

- Alembic 管理；
- MySQL 8；
- 金额 Decimal；
- 业务编号 UNIQUE；
- FK 使用 ID；
- 核心索引来自真实查询场景；
- 当前成本价更新必须原子重算并保存派生价格与既有审计字段；
- 商品字段来自真实大表。
