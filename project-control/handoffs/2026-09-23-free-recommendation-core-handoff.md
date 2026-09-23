# Handoff：自由推品 B 核心（B → A/C）

## 已完成

B 分支 `feat/free-recommendation-core` 已新增：

- `recommendation/application/service.py`：Run、结构化需求、类目池、候选检索/持久化、人工确认。
- `recommendation/infrastructure/`：对 Revision `20260923_0039` 已有表的 ORM Model 与 Repository；**未新增 Migration**。
- `recommendation/api/recommendation_router.py`：B-owned Router，尚未写入 API 总聚合。
- `tests/recommendation/test_recommendation_core_service.py`：真实 MySQL 集成链路覆盖。

## C 调用边界

C 的 AgentRunner 只能调用 `RecommendationService`：

1. `begin_analysis(run_id)`；
2. `save_parsed_requirement(run_id, ParsedRequirement, provider, model, prompt_version)`；
3. `category_pool(run_id)`；
4. `record_category_choices(run_id, choices)`；
5. `search_products(run_id, category_paths)`；
6. `persist_ranked_candidates(run_id, payload)`；
7. `mark_no_candidates`、`mark_needs_input`、`mark_failed`。

AI 不能持有 Repository/Session，不能自己生成数据库商品或供应商。`ParsedRequirement` 当前支持毛利率下限、京东价范围、品牌/类目/场景关键词和履约模式；新增确定性筛选字段须先由 B 扩展 Schema 与 Repository。

## A 最终集成

在 API V1 聚合 Router 中 include B Router。B 已使用 `/recommendation-projects` 前缀；完整路径应为：

- `POST /api/v1/recommendation-projects/{project_id}/runs`
- `GET /api/v1/recommendation-projects/{project_id}/runs`
- `GET /api/v1/recommendation-projects/runs/{run_id}`
- `GET /api/v1/recommendation-projects/runs/{run_id}/candidates`
- `PATCH /api/v1/recommendation-projects/candidates/{candidate_id}/confirmation`

## Migration Requirement（由 A 评审并创建）

导出前需要补齐以下合同：

1. Recommendation 专用导出文件记录，至少关联 Project、Run、Template File、Mapping、导出 File、版本、导出人和时间；不要复用语义不一致的 `QUOTED_EXPORT`。
2. `factory_direct` 的人工确认字段（是/否/待确认），不能由 Agent 或现有 Product 字段推断。
3. 定义导出文件的受控 `BidFileType` 或同等独立文件引用，确保历史导出可下载和追溯。

在这些字段合入前，B 不应生成不可追溯或猜测“厂家直供”的客户 Excel。
