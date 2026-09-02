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

# Sprint 2：Supplier Product Quote

- `scm_supplier_product_quote`

建议字段包含：

- id
- quote_archive_no
- supplier_id
- product_id NULL
- brand / brand_id（最终按数据模型冻结）
- product_model（大小写敏感）
- tax_included_factory_price
- product_spec_params
- valid_until
- quote_remark
- quote_status
- source
- entered_by
- entered_at
- void fields

---

# Sprint 3：Product Master

至少存在：

- `scm_product`
- 商品分类相关表（如需要）
- 品牌相关表（如需要）
- 参数扩展相关表（如需要）

是否拆品牌、分类、参数表，必须以真实大表字段和检索需求决定。

明确：

- 不默认创建 `scm_product_sku`
- 不默认创建 `scm_supplier_sku`

---

# Sprint 4：Product Import

- `scm_import_task`
- `scm_import_row`
- `scm_import_row_error`

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
- 历史报价不可覆盖；
- 商品字段来自真实大表。
