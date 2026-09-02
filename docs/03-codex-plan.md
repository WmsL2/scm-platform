# Codex 开发计划 V1.3.2

## Sprint 0：企业底座

只做：

- Monorepo
- Vue
- FastAPI
- SQLAlchemy Async
- Alembic
- MySQL配置
- Local-First adapters
- Logging
- Error
- Response
- Health
- Test/Lint/Typecheck
- CI
- project-control

不做业务模块。

## Sprint 1：Auth/RBAC + Supplier

建议任务：

1. Business Sequence
2. User/Role/Permission
3. JWT
4. Permission Dependency
5. Supplier table/model
6. Supplier CRUD
7. Contact
8. Qualification
9. Archive workflow
10. Audit
11. Frontend
12. Tests + Docs

## Sprint 2：Supplier Product Quote

1. Quote Schema
2. Create/List/Detail
3. Valid Supplier Selector
4. Case-sensitive model search
5. VOID / Copy New
6. Effective Quote Query
7. Compare
8. Optional product_id link
9. Frontend
10. Tests + Docs

## Sprint 3：Catalog / Product Master

第一步不是写表。

必须先读取真实《大表模版.xlsx》并输出：

`Product Master Data Dictionary`

冻结：

- 每列含义
- 类型
- 必填
- 枚举
- 索引
- 检索需求
- 唯一性/去重策略
- 更新策略
- 是否单独字典/参数化

然后才创建 `scm_product` 等正式 Migration。

一期不强制 SPU/SKU。

## Sprint 4：Product Master Import

- 固定模板
- Header
- Row Validation
- Duplicate/Conflict
- Staging
- Error
- Preview
- Confirm Import
- Idempotency
- 正式写入 scm_product

禁止 AI Field Mapping。

## Sprint 5：Requirement + Matching + Quotation

匹配商品只查询正式商品主数据。

## Sprint 6：Solution

从正式商品主数据选品。

## Sprint 7：Acceptance

安全、性能、真实数据、备份恢复、部署、验收。

---

# 每次任务结束

必须：

1. 测试；
2. Module Status；
3. Change Record；
4. 未完成写 Handoff；
5. 必要时 CURRENT_STATUS；
6. 正式文档同步；
7. 必要时 ADR；
8. 最终报告。
