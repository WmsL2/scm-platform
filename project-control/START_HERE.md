# START HERE / 新成员与新 Agent 入口

开始任何任务：

1. 读根目录 `AGENTS.md`
2. 读 `CURRENT_STATUS.md`
3. 读 `ROADMAP.md`
4. 读当前 Sprint
5. 读对应 Module Status
6. 查看最近相关 Change
7. 查看 Handoff
8. 查看 ADR
9. 读当前 Prompt

然后检查：

- Git Branch
- 是否存在同模块 Active Branch
- 是否有未完成 Handoff
- Alembic heads
- main 是否可运行

结束任务前：

- Test
- Module Status
- Change Record
- Handoff（如未完）
- CURRENT_STATUS（如影响）
- 正式 Docs
- ADR（如重要决策）

文档未同步不算完成。

## Project Control Gate / 项目控制门禁

Definition of Done = Code + Database + Tests + Documentation + Project Status。

任何修改 `project-control/` 之外内容的 PR，必须同时包含：

1. `project-control/changes/**` 下的 Change Record（变更记录）；
2. `project-control/CURRENT_STATUS.md`、`project-control/modules/**` 或
   `project-control/sprints/**` 中至少一项状态更新。

GitHub Actions 的 `project-control` Job 会自动检查上述要求；不满足即禁止 Merge。
GitHub 是 Merge SHA、合入时间等仓库事实的 Source of Truth（事实来源），无需为每次
变更人工抄写这些信息。
