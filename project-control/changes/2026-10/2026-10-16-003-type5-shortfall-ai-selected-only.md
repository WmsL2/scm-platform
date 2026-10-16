# 2026-10-16-003：类型 5 短缺时仅展示 AI 匹配商品

Change ID：2026-10-16-003  
Module：Recommendation / Type 5 PPT Solution  
Author / Agent：Codex  
Date：2026-10-16  
Branch：`codex/fix/type5-shortfall-show-matched-only`  
Commit：待提交

## Goal

修正类型 5 单品价格档短缺时展示完整冻结池的问题。数量不足仍提示并允许人工确认，但候选表只显示 AI 在各价格档实际匹配出的商品。

## Modified Files

- `apps/api-server/app/modules/recommendation/application/ppt_service.py`
- `apps/api-server/tests/recommendation/test_ppt_solution_plans.py`
- `apps/api-server/tests/recommendation/test_ppt_plan_runner.py`
- `apps/web-admin/src/views/bid/PptSolutionWorkspaceView.vue`
- `apps/web-admin/src/views/bid/PptSolutionWorkspaceView.spec.ts`
- `project-control/CURRENT_STATUS.md`
- `project-control/modules/recommendation.md`

## Created Files

- `project-control/decisions/ADR-0068-type5-direct-shortfall-ai-selected-only.md`
- `project-control/changes/2026-10/2026-10-16-003-type5-shortfall-ai-selected-only.md`

## Database / Alembic

Revision：无。

## API / Permission Changes

无；复用现有 Run、候选分页、确认接口和 `recommendation:review` 权限。

## Business Rule Changes

- 任一价格档有合格候选时，仍执行 AI 匹配。
- 短缺档的匹配数量为该档实际可用数与目标数的较小值。
- 只保存 AI 匹配结果；完整冻结池及价格档外商品不进入人工确认表。
- 所有价格档都无匹配商品时保持失败。

## Tests

```powershell
cd apps/api-server
.\.venv\Scripts\python.exe -m pytest tests/recommendation/test_ppt_solution_plans.py tests/recommendation/test_ppt_plan_runner.py tests/recommendation/test_ppt_selection_adapter.py tests/recommendation/test_recommendation_core_service.py
.\.venv\Scripts\python.exe -m ruff check app/modules/recommendation/application/ppt_service.py tests/recommendation/test_ppt_solution_plans.py tests/recommendation/test_ppt_plan_runner.py
.\.venv\Scripts\python.exe -m mypy app/modules/recommendation/application/ppt_service.py

cd ..\web-admin
npm run test -- --run src/views/bid/PptSolutionWorkspaceView.spec.ts
npm run typecheck
npm run build
```

Result：后端 28 passed；Ruff、Mypy 通过；前端 Vitest 2 passed；前端类型检查和生产构建通过。生产构建仅保留既有的大包体提示。

## Remaining Work

- 完成自动化验证与项目控制门禁。
- 部署后完成浏览器验收：例如目标 15 件、该档可用 10 件时，页面应仅显示 AI 匹配的 10 件，并保留不足提示。
