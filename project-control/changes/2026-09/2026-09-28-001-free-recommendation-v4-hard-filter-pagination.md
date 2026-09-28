# Change Record：自由推品 V4 全量硬条件筛选与分页确认

日期：2026-09-28  
分支：`codex/fix/free-recommendation-hard-constraints`

## 变更

- Agent 只解析价格、折扣率、点位等数值硬条件；场景、类目、数量、价格有效期及其他非数值上下文不再进入筛选 JSON。
- 移除 AI 类目方向选择、每类检索、30 条截断、模型排序和逐条推荐理由；服务层改为持久化全部符合硬条件的候选快照。
- 候选查询改为分页，返回总数、已确认数和待确认数；前端支持翻页、全选本页、全选全部待确认商品、清空选择和服务端全量批量确认。
- 候选表移除“推荐理由”，保留“评分”列并展示商品主数据 `positive_rating`。
- 页面中的业务别名“点位”改为对应商品字段名称“毛利率”，并按百分比展示（如 `0.4130` 显示为 `41.30%`）。
- Run 生命周期允许 V4 从 `RETRIEVING` 直接进入 `CANDIDATES_READY`，因为该路径不再有 AI 排序阶段。
- 已有历史 Run 及其候选快照保持不变。

## Migration

无。复用既有 `scm_recommendation_run`、`scm_recommendation_candidate`、`scm_recommendation_confirmation`。

## 验证

- 后端：`.venv\\Scripts\\python.exe -m ruff check app/modules/recommendation tests/recommendation`；`.venv\\Scripts\\python.exe -m pytest tests/recommendation -q`。
- 前端：`npm run typecheck -- --pretty false`；`npm test -- --run src/api/recommendation.spec.ts src/views/bid/RecommendationWorkspaceView.spec.ts`。
- 根目录：`git diff --check`。
