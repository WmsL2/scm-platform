# Database Reference

本目录只保存设计参考。

正式数据库 Schema：

> 必须由 `apps/api-server/migrations/` 中的 Alembic Revision 管理。

当前不提供“一次性全量业务DDL”，原因：

1. Sprint 0 不应创建全部业务表；
2. 商品主数据结构已更新为“大表一行 = 一条具体商品”；
3. `scm_product` 最终字段和唯一键尚需根据真实大表模板冻结；
4. 旧版 SPU/SKU 结构不得作为最终设计继续执行。

开发各 Sprint 时按照 `docs/08-database-roadmap.md` 创建对应 Revision。
