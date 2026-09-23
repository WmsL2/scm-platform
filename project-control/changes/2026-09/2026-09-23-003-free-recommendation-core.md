# Change Record：自由推品 B 核心

日期：2026-09-23  
模块：recommendation

## 本次实现

- 新增 B-owned 的 Recommendation Run、类目选择、候选、人工确认 ORM Model、Repository、Application Service 与独立 API Router。
- 创建 Run 仅允许 `FREE_RECOMMENDATION` 项目，且要求最新 `RECOMMENDATION_TEMPLATE` 映射已人工确认；项目备注以不可变原文快照保存。
- 结构化需求由 Pydantic 校验后才可参与商品查询；固定过滤 ACTIVE 商品、ARCHIVED + NORMAL 的未删除供应商，并按毛利率、京东价、品牌和类目条件检索。
- Agent 只能通过 B Service 保存解析、读取类目池、读取精简商品候选、落库排序结果；不直接访问正式商品库。
- 候选入库保存商品、供应商和价格快照；人工确认前再次校验候选当前仍合格。

## 未完成 / 依赖

- 未注册总 API Router：按 A/B/C 所有权约定，由 A 的最终集成处理。
- 未实现 DeepSeek、AgentRunner、任务队列和前端：属于 C。
- 未实现 Excel 导出：目前没有 Recommendation 专用导出文件记录，模板 `factory_direct` 也没有对应的人工确认字段；已在 B→A/C Handoff 中提出最小 Migration Requirement。

## 验证

- `python -m pytest tests/recommendation -q`：16 passed。
- `python -m ruff check app/modules/recommendation tests/recommendation/test_recommendation_core_service.py`：通过。
- `python -m mypy app/modules/recommendation`：通过。
- Alembic：单 Head `20260923_0039`，本次无新增 Revision。
