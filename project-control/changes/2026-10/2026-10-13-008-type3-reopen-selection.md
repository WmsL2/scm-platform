# 类型 3 返回调整选品

日期：2026-10-13  
状态：IMPLEMENTED / BROWSER_ACCEPTANCE_PENDING

## 背景

类型 3 项目完成选品后进入 `READY`，或导出后进入 `EXPORTED`。原工作台与 API 没有返回 `SELECTING` 的动作，但重新生成候选又明确要求先返回待选品，导致项目无法调整。

## 变更

- 新增 `POST /api/v1/type3-recommendation-projects/{project_id}/runs/{run_id}/commands/reopen-selection`。
- 仅允许 `READY` / `EXPORTED` 的项目返回 `SELECTING`，并要求当前 Run 至少有一件已确认候选。
- 已确认候选、导出记录、来源 Sheet 和冻结快照均保留；Run 从 `EXPORTED` 回到 `CONFIRMED`，后续导出仍按既有版本规则产生新版本。
- 写入 `TYPE3_SELECTION_REOPENED` 审计事件，保留原项目状态。
- 类型 3 Run 响应增加只读 `project_status`，前端据此在 `SELECTING` 显示“完成选品”，在 `READY` / `EXPORTED` 显示“返回调整选品”。
- 修复启动生成后的前端时序：创建 Run 返回时可能仍携带旧 `MATCHING` 状态；页面完成 Run 列表刷新后改用该 Run 的最新条目，后端的单 Run 读取也返回当前项目状态，因此候选生成完成后无需浏览器刷新即可显示“完成选品”。

## API / UI / Permission

- 新增上述回退 API。
- 工作台新增“返回调整选品”按钮。
- 复用既有 `recommendation:review` 权限；无新增权限。

## 数据库

- 无 Alembic Revision，无表或数据迁移。

## 验证

- `python -m pytest`（全部 `test_type3_*.py`）：10 passed。
- `python -m ruff check app/modules/type3_recommendation tests/recommendation/test_type3_reopen_selection.py`：通过。
- `python -m mypy app/modules/type3_recommendation`：通过。
- `npm run typecheck`、`npm run build`：通过。

## 未完成

- 需在浏览器使用已完成选品和已导出两种真实类型 3 项目验收回退、重新确认和递增版本导出。
