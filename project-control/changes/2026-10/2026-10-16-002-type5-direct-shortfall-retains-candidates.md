# 2026-10-16-002：类型 5 单品价格档短缺保留候选

Change ID：2026-10-16-002  
Module：Recommendation / Type 5 PPT Solution  
Author / Agent：Codex  
Date：2026-10-16  
Branch：`codex/fix/type5-show-partial-candidates`  
Commit：待提交

## Goal

当类型 5 单品价格档的合格商品少于配置目标时，保留短缺提示，但显示并允许人工确认所有已经冻结的合格商品，而不是将 Run 标记失败并隐藏全部候选。

## Created Files

- `project-control/decisions/ADR-0067-type5-direct-shortfall-retains-candidates.md`
- `project-control/changes/2026-10/2026-10-16-002-type5-direct-shortfall-retains-candidates.md`

## Modified Files

- `apps/api-server/app/modules/recommendation/application/ppt_service.py`
- `apps/api-server/tests/recommendation/test_ppt_solution_plans.py`
- `apps/web-admin/src/views/bid/PptSolutionWorkspaceView.vue`
- `apps/web-admin/src/views/bid/PptSolutionWorkspaceView.spec.ts`
- `project-control/modules/recommendation.md`
- `project-control/CURRENT_STATUS.md`

## Deleted Files

无。

## Database / Alembic

Revision：无。

## API Changes

无；复用现有 Run、候选分页和确认接口。

## UI Changes

- 价格档短缺的单品 Run 显示短缺警告，同时显示已保留的候选表和人工确认控件。
- 候选摘要明确区分“已保留合格商品”和正常的“AI 最终匹配”。

## Permission Changes

无；复用既有 `recommendation:review`。

## Business Rule Changes

- 单品价格档 `item_count` 是目标数量，不再是隐藏合格候选的失败门槛。
- 任一价格档短缺时，保留本 Run 全部冻结合格候选，不调用 AI 排序，进入待人工确认状态。
- 零候选和提供方/合同失败路径保持不变。

## Tests

Command：

```powershell
cd apps/api-server
.\.venv\Scripts\python.exe -m pytest tests/recommendation/test_ppt_solution_plans.py tests/recommendation/test_ppt_plan_runner.py tests/recommendation/test_ppt_selection_runner.py tests/recommendation/test_ppt_selection_adapter.py tests/recommendation/test_recommendation_core_service.py
.\.venv\Scripts\python.exe -m ruff check app/modules/recommendation/application/ppt_service.py tests/recommendation/test_ppt_solution_plans.py
.\.venv\Scripts\python.exe -m mypy app/modules/recommendation/application/ppt_service.py

cd ..\web-admin
npm run test -- --run src/views/bid/PptSolutionWorkspaceView.spec.ts
npm run typecheck
npm run build
```

Result：后端 29 passed；Ruff 通过；Mypy 通过；前端 Vitest 2 passed；前端类型检查与生产构建通过。

## Known Issues

- 历史失败 Run 不回写；部署后需要重新生成，才会以待人工确认状态保留候选。
- 服务器浏览器验收待完成：配置目标数高于实际合格数时，应显示短缺提示、全部候选和确认按钮。

## Remaining Work

- 执行项目控制门禁。
- 完成服务器浏览器验收。

## Next Step

部署后以“目标 8 件、实际 3 件”的单品价格档重新生成，确认 3 件候选可见、可确认并可进入 PPT 生成。
