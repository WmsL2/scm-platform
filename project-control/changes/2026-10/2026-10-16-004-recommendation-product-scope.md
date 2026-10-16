# 2026-10-16-004：类型 1--5 所属公司与采销员选品范围

Change ID：2026-10-16-004  
Module：Bid / Matching / Recommendation / Type 3 / Catalog  
Author / Agent：Codex  
Date：2026-10-16  
Branch：`codex/feat/recommendation-company-purchaser-scope`  
Commit：待提交

## Goal

在类型 1--5 各自详情工作台中，允许操作人于发起选品前多选所属公司和采销员；随后只从交集范围内的合格正式商品进行匹配或推品。

## Modified Files

- `apps/api-server/app/modules/bid/api/router.py`
- `apps/api-server/app/modules/bid/application/service.py`
- `apps/api-server/app/modules/bid/infrastructure/models.py`
- `apps/api-server/app/modules/bid/schemas.py`
- `apps/api-server/app/modules/catalog/infrastructure/models.py`
- `apps/api-server/app/modules/matching/application/service.py`
- `apps/api-server/app/modules/matching/infrastructure/repository.py`
- `apps/api-server/app/modules/recommendation/application/ppt_catalog_service.py`
- `apps/api-server/app/modules/recommendation/application/service.py`
- `apps/api-server/app/modules/recommendation/infrastructure/models.py`
- `apps/api-server/app/modules/recommendation/infrastructure/ppt_repository.py`
- `apps/api-server/app/modules/recommendation/infrastructure/repository.py`
- `apps/api-server/app/modules/type3_recommendation/application/service.py`
- `apps/api-server/app/modules/type3_recommendation/infrastructure/models.py`
- `apps/web-admin/src/api/bid.ts`
- `apps/web-admin/src/types/bid.ts`
- `apps/web-admin/src/views/bid/BidMatchingWorkbenchView.vue`
- `apps/web-admin/src/views/bid/PptSolutionWorkspaceView.vue`
- `apps/web-admin/src/views/bid/RecommendationWorkspaceView.vue`
- `apps/web-admin/src/views/bid/Type3CategoryWorkspaceView.vue`
- `project-control/CURRENT_STATUS.md`
- `project-control/modules/catalog.md`
- `project-control/modules/recommendation.md`

## Created Files

- `apps/api-server/alembic/versions/20261016_0058_recommendation_product_scope.py`
- `apps/api-server/app/modules/bid/domain/product_scope.py`
- `apps/api-server/tests/bid/test_product_scope.py`
- `apps/api-server/tests/matching/test_matching_product_scope.py`
- `apps/web-admin/src/views/bid/RecommendationProductScopeForm.vue`
- `project-control/decisions/ADR-0069-recommendation-product-company-purchaser-scope.md`
- `project-control/changes/2026-10/2026-10-16-004-recommendation-product-scope.md`

## Database / Alembic

Revision：`20261016_0058`（基线 `20261015_0057`）。

- `scm_bid_project`：两个可编辑范围字段。
- `scm_match_task`、`scm_recommendation_run`、`scm_type3_recommendation_run`：执行范围冻结快照。
- `scm_product`：新增 `(status, purchasing_agent)` 索引。

## API / UI / Permission Changes

- 新增 `PUT /api/v1/bid-projects/{project_id}/recommendation-scope`，复用 `bid:update`。
- 类型 1/2、3、4、5 工作台均显示“商品选品范围”卡片；同字段多选为 OR，两字段同时设置为 AND，空选保持全量合格商品。
- 商品候选下拉复用既有 Product Filter Options 接口，因此加载选项仍遵从 `product:list` 的数据可见性；保存范围使用 `bid:update`。

## Follow-up: Empty Result Visibility

- 类型 4、5 的工作台始终读取 Run 历史中最新的一条，`NO_CANDIDATES` 不再被历史成功 Run 覆盖。
- 类型 3、4、5 会在页面上持续显示本次商品范围无候选的提示；类型 5 后台运行结束后刷新页面也不会回显旧候选。
- 类型 1、2 的启动响应新增候选商品数和命中需求行数；候选池为零或需求零命中时，工作台显示准确提示而非一律显示“匹配完成”。

## Follow-up: Type 3 Candidate Display Columns

- 类型 3 候选商品表新增与类型 4、5 一致的“自定义显示列”。商品图片、SKU、商品名称和来源 Sheet 固定显示；其余商品主数据字段可按勾选顺序显示。
- 用户选择仅保存在当前浏览器的 `localStorage`（`scm.type3-candidates.visible-columns.v1`）；不修改本次 Run 的冻结候选、确认状态、Sheet 隔离或导出映射。
- 无 Migration、接口或权限变化。

Follow-up Result：类型 3 / 4 / 5 工作台 Vitest `15 passed`、前端类型检查与生产构建通过（仅保留既有大包体警告）；本机 Vite 启动成功，真实浏览器点击验收待完成。

## Tests

```powershell
cd apps/api-server
.\.venv\Scripts\python.exe -m ruff check app/modules/bid app/modules/matching app/modules/recommendation app/modules/type3_recommendation app/modules/catalog tests/bid/test_bid_routes.py tests/bid/test_product_scope.py tests/matching/test_matching_product_scope.py
.\.venv\Scripts\python.exe -m mypy app/modules/bid app/modules/matching app/modules/recommendation app/modules/type3_recommendation
.\.venv\Scripts\python.exe -m pytest tests/bid/test_bid_routes.py tests/bid/test_product_scope.py tests/matching/test_matching_product_scope.py tests/recommendation/test_free_recommendation_service.py tests/recommendation/test_type3_run_scope.py -q
.\.venv\Scripts\alembic.exe heads

cd ..\web-admin
npm run typecheck
npm run build
```

Result：Ruff 通过；Mypy `66 source files` 通过；后端定向 `17 passed`；Alembic 单一 head 为 `20261016_0058`，本机当前 Revision 也为 `20261016_0058`；前端类型检查和生产构建通过（仅保留既有大包体警告）。

Follow-up Result：后端 Matching Ruff/Mypy 通过、定向 `5 passed`；前端工作台定向 Vitest `21 passed`、类型检查和生产构建通过（仅保留既有大包体警告）。

## Remaining Work

- 在浏览器中以至少一个类型 1--5 项目验收：保存多选、重新生成、范围内候选和历史 Run 不回写。
- 本机真实 MySQL Matching 集成回归当前为 `3 passed, 1 failed`；失败用例在共享开发商品池中命中了历史同型号商品，需隔离测试商品池后再作为完整回归结论。
