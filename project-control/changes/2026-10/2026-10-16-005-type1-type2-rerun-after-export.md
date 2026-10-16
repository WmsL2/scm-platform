# Change 2026-10-16-005：类型 1/2 导出后重新生成

日期：2026-10-16
分支：`fix/type1-type2-matching`

## 问题

类型 1/2 导出回填表后项目进入 `EXPORTED`。前端只在 `IMPORTED / SELECTING / READY` 显示匹配按钮，后端也拒绝从 `EXPORTED` 启动匹配，导致用户无法按类型 3/4 的节奏重新生成推荐。

## 变更

- 类型 1/2 工作台和旧详情入口在 `EXPORTED` 状态继续显示“重新生成推荐”。
- 重新生成前提示：创建新的匹配任务并刷新当前推荐结果，已有导出文件和历史匹配记录继续保留。
- 类型 1、类型 2 专属后端编排及兼容回退路径均允许从 `EXPORTED` 启动。
- 每次重跑继续创建独立 MatchTask、MatchCandidate 和 Selection；需求行的 `current_selection_id` 指向本次新结果，历史记录不覆盖。
- 重跑成功后项目进入 `READY`，允许再次导出；失败时恢复启动前的 `EXPORTED` 状态。

## 验证

- 后端完整 Matching 测试集：`51 passed`；其中类型 1/2 MySQL 集成覆盖 `EXPORTED` 重跑、新任务和新当前 Selection、历史任务与 Selection 保留。
- 前端工作台及详情页 Vitest：`11 passed`。
- Ruff：通过。
- Mypy 与前端 TypeScript 类型检查：通过。

## 影响

- Alembic Revision：无。
- API：无新增路径，复用 `POST /api/v1/bid-projects/{project_id}/commands/start-matching`。
- UI：导出后新增“重新生成推荐”入口及二次确认说明。
- Permission：继续使用 `bid:match`。
- AI 与类型边界：类型 1/2 仍调用各自独立 Agent、Prompt 和规则；本次只扩展允许启动的项目状态。

## 待验收

- 使用真实类型 1、类型 2 项目完成“匹配 → 导出 → 重新生成 → 再次导出”，确认旧文件仍可下载且新结果按当前商品数据生成。
