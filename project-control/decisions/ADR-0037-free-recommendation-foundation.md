# ADR-0037：自由推品项目与推荐数据底座

状态：ACCEPTED  
日期：2026-09-23

## 决策

- `scm_bid_project` 继续是统一项目壳；类型 1–3 为 `FILTER_RECOMMENDATION`，类型 4 为 `FREE_RECOMMENDATION`，`PPT_SOLUTION` 本期不开放。
- 类型 4 没有客户需求 Excel，使用至少 20 字的需求说明和每项目版本化 `RECOMMENDATION_TEMPLATE`。模板及映射历史均不可覆盖。
- 模板读取是确定性的 Excel 结构分析；仅预映射冻结字段，“毛利”必须由用户确认是 `profit` 或 `gross_margin`。
- Recommendation Run 生命周期独立于 Project 生命周期。推荐表只保存 Product/Supplier 快照和引用，不修改 Product 或 Supplier；AI 不直连业务库。
- Migration `20260923_0039` 一次性建立推荐 Schema 和权限。后续 B/C 不得为本模块新增 Migration。
- FILTER 项目携带自由推品模板会明确拒绝；类型 4 模板和映射仅属于 FREE 项目。对象存储写入若数据库事务失败必须补偿删除。
- 0038 Schema 不能表达类型 4 数据；若存在本 Revision 新业务数据，Migration downgrade 明确拒绝而不静默删除数据。
