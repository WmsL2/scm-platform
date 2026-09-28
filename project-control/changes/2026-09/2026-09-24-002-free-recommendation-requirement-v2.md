# Change Record：自由推品 Requirement V3 硬条件收敛

日期：2026-09-24
分支：`feat/free-recommendation-requirement-v2`（基于最新 main）

## 变更

- 以业务新结论覆盖 V2 人工核验设计：新 Run 不再生成或更新人工核验，单条确认、批量确认和导出不再检查 `manual_flags`；历史 JSON 保持读取兼容。
- 确定性筛选仅保留明确类目（含排除）和数值价格条件：协议价、明确京东价、折扣率及点位。未指明口径的价格默认解释为协议价。
- 点位复用商品既有 `gross_margin` 字段，百分比采用小数表达（6% 为 `gross_margin_min=0.06`）。
- 品牌、场景、节日、人群、物流、一件代发、库存、厂家直发、销量、评分和卖点调整为受控参考信息，不会硬过滤、要求补充信息或阻塞确认/导出。
- 移除人工核验 API、DTO、前端编辑/勾选门禁；候选工作台聚焦排名、商品、品牌、协议价、折扣率、点位、推荐分、理由和确认状态。
- 保留模板派生字段 `supports_jd_or_sf`，无新增 Migration。

## Migration

无。复用既有 `RecommendationRun.parsed_requirement`、`RecommendationCandidate.manual_flags` 和冻结商品快照。

## 验证

- 后端执行 `ruff check .`、`mypy app`、`pytest -q tests/recommendation`、`pytest -q`。
- 前端执行 `npm run typecheck`、`npm run test -- --run`、`npm run build`。
- 根目录执行 `git diff --check` 与 `git status --short`。
