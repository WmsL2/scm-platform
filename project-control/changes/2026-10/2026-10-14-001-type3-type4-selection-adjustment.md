# 类型 3/4 选品确认调整与类型 3 冻结详情

日期：2026-10-14  
状态：IMPLEMENTED / BROWSER_ACCEPTANCE_PENDING

## 背景

类型 3、类型 4 在完成选品后虽可返回 `SELECTING`，但页面缺少撤销已确认商品的完整入口；类型 3 没有候选商品详情，人工无法在不离开工作台的情况下查看本次选品依据。

## 变更

- 类型 4 新增 `POST /api/v1/recommendation-projects/runs/{run_id}/unconfirmations`，支持指定候选或全选已确认候选的批量撤销；仅 `SELECTING` 可撤销，且撤销写入项目审计事件。
- 类型 3 新增 `POST /api/v1/type3-recommendation-projects/runs/{run_id}/candidate-unconfirmations`，支持指定候选或按当前 Sheet/全部 Sheet 撤销已确认候选；仅 `SELECTING` 且可人工确认的 Run 可执行。
- 类型 3 单条与批量撤销都会保留 Run、候选及历史导出；最后一件确认被撤销时 Run 回到 `WAITING_CONFIRMATION`。
- 类型 3 候选表新增“查看详情”，展示本次 Run 冻结的商品、价格和图片引用快照，不查询当前商品主数据，避免历史决策依据漂移。
- 两类工作台在返回调整后显示明确提示：可以继续确认或撤销确认，历史导出文件不会被修改。
- 类型 3、类型 4 的“全选全部待确认/已确认”操作会先重新读取当前 Run 和候选汇总；类型 3 同时同步当前 Run 状态。确认或撤销后无需刷新浏览器，下一次全选与批量撤销会使用最新数量。

## API / UI / Permission

- 新增类型 3 撤销确认 API。
- 类型 3、类型 4 均增加已确认候选的单条/批量撤销及全选本页/全部范围选择；类型 3 另有冻结快照详情。
- 复用 `recommendation:review`，无新增权限。

## 数据库

- 无 Alembic Revision；复用候选确认字段、类型 4 确认记录及项目事件审计表。

## 验证

- `python -m pytest tests/recommendation -k type3 -q`：14 passed。
- `python -m pytest tests/recommendation/test_recommendation_core_service.py -q`：4 passed。
- `python -m ruff check app/modules/type3_recommendation app/modules/recommendation/application/service.py tests/recommendation/test_type3_candidate_confirmation.py`：通过。
- `python -m mypy app/modules/type3_recommendation app/modules/recommendation/application/service.py`：通过。
- `npm run test -- --run src/api/recommendation.spec.ts src/views/bid/RecommendationWorkspaceView.spec.ts src/views/bid/Type3CategoryWorkspaceView.spec.ts`：13 passed。
- `npm run typecheck`、`npm run build`：通过。

## 未完成

- 需使用已完成选品和已导出的真实类型 3、类型 4 项目，在浏览器验收返回调整、单条/批量撤销、重新确认和递增版本导出。
