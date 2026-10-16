# ADR-0070：类型 1/2 导出后允许重新生成

状态：ACCEPTED
日期：2026-10-16

## 背景

类型 1/2 的导出会把项目推进到 `EXPORTED`。客户需求、商品主数据或报价可能随后调整，用户需要像类型 3/4 一样重新生成推荐；旧实现只允许 `IMPORTED / SELECTING / READY` 启动匹配，导出后流程被锁死。

## 决策

- 类型 1/2 允许从 `SELECTING / READY / EXPORTED` 重新执行原有 start-matching 命令，不新增平行 API。
- 每次执行创建新的 MatchTask、候选及 Selection，不覆盖或删除历史匹配记录。
- 新结果通过需求行 `current_selection_id` 成为当前推荐；历史导出附件继续保留。
- 从 `EXPORTED` 重跑成功后进入 `READY`，用户可生成新的导出版本。
- 远程 AI 或结构化合同失败时恢复执行前状态；从 `EXPORTED` 发起的失败不得影响已有导出文件。
- 类型 1、2 只共享重新生成入口和生命周期语义，各自 Agent、Prompt、召回、协议价和结果规则保持独立。

## 后果

- 不新增数据库表、字段或 Alembic Revision。
- 不新增 API 路径或权限，继续复用 `bid:match`。
- 页面明确提示重新生成会刷新当前推荐，但会保留历史匹配与导出文件。
- 提交投标后的 `SUBMITTED` 及 `WON / LOST / VOIDED` 终态不允许重新生成。
