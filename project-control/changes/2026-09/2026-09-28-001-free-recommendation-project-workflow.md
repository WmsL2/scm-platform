# 2026-09-28 类型4自由推品项目工作流

## 背景

原工作台能够生成和确认候选，但项目状态没有随推荐、人工选品、导出和投标结果形成闭环；确认后的商品也缺少明确的左右对照和后续业务动作。

## 变更

- 项目创建后为 `IMPORTED`；启动推荐自动进入 `MATCHING`；候选持久化完成后自动进入 `SELECTING`。
- 推荐失败、取消、需要补充或没有候选时恢复至可继续处理状态：已有历史候选回到 `SELECTING`，否则回到 `IMPORTED`。
- 人工至少选择一件商品后可完成选品并进入 `READY`；导出确认结果后进入 `EXPORTED`。
- 类型4项目允许使用最新 `RECOMMENDATION_EXPORT` 标记为 `SUBMITTED`，随后沿用投标项目既有接口登记 `WON / LOST`。
- `READY / EXPORTED` 支持返回 `SELECTING` 调整；历史导出不删除，再次导出使用新版本。
- 工作台改为左右双栏，左侧展示 Agent 推荐，右侧展示人工选择；候选点击高亮，支持加入、编辑和移除。
- 项目列表、普通详情和工作台统一显示有颜色的状态标签。
- 新增完成选品、返回调整选品和移除人工确认接口。

## API / 权限

- `DELETE /api/v1/recommendation-projects/candidates/{candidate_id}/confirmation`，权限 `recommendation:review`。
- `POST /api/v1/recommendation-projects/{project_id}/runs/{run_id}/commands/complete-selection`，权限 `recommendation:review`。
- `POST /api/v1/recommendation-projects/{project_id}/runs/{run_id}/commands/reopen-selection`，权限 `recommendation:review`。
- 既有导出、提交及结果登记接口和权限不变。

## 数据库

- Alembic Revision：无。
- 复用既有项目、事件、候选、人工确认和导出版本表。

## 验证

- Recommendation 后端测试覆盖自动状态推进、人工确认增删、完成选品、返回调整、导出、提交和中标登记。
- 前端工作台组件测试、TypeScript 类型检查和生产构建纳入回归。

