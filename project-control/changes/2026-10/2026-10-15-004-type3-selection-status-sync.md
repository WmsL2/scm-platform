# 类型 3 候选状态同步与历史恢复

日期：2026-10-15  
状态：COMPLETED  
分支：`fix/type3-selection-status-sync`

## 背景

类型 3 Run 已生成候选并进入 `WAITING_CONFIRMATION` 后，所属项目仍保留 `MATCHING`。工作台只在项目为 `SELECTING` 时开放勾选、确认和撤销确认，因此候选可见但无法人工处理。

## 变更

- Run 候选写入完成且计数大于零时，在同一事务中将项目 `MATCHING -> SELECTING`，并写入 `TYPE3_CANDIDATES_READY` 审计事件。
- 新增 `POST /api/v1/type3-recommendation-projects/{project_id}/runs/{run_id}/commands/recover-selection`，仅供历史卡住 Run 使用。
- 恢复命令需要 `recommendation:review`，并校验 Run 归属、Run 状态为 `WAITING_CONFIRMATION`、候选数量大于零、项目状态仍为 `MATCHING`；成功后写入 `TYPE3_SELECTION_RECOVERED`。
- 工作台在上述历史状态显示“恢复待选品”按钮；恢复不会重新调用 DeepSeek 或重新生成候选。

## 影响边界

- Alembic Revision：无。
- 新增恢复 API 与前端操作按钮；沿用既有 `recommendation:review` 权限。
- 不改商品、类目、候选快照或 AI 调用合同；不直接修改任何既有业务项目数据。

## 验证

- `apps/api-server/.venv/Scripts/python.exe -m pytest apps/api-server/tests/recommendation/test_type3_selection_status_sync.py apps/api-server/tests/recommendation/test_type3_reopen_selection.py apps/api-server/tests/recommendation/test_type3_candidate_confirmation.py apps/api-server/tests/recommendation/test_type3_run_scope.py -q`：9 passed。
- `apps/api-server/.venv/Scripts/python.exe -m ruff check apps/api-server/app/modules/type3_recommendation apps/api-server/tests/recommendation/test_type3_selection_status_sync.py`：通过。
- `npm run typecheck`（`apps/web-admin`）：通过。

## 待验收

- 部署后打开历史项目，点击“恢复待选品”，确认候选复选框和批量确认按钮可用，且不产生新的 AI 请求。
