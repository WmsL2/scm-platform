# Change Record: Project Control Governance Hardening

Change ID: 2026-09-03-008
Module: project-control
Branch: chore/project-control-governance

- 新增 Project Control PR Gate：非 `project-control/` 修改必须同时包含 Change Record 与状态文档更新。
- 新增 GitHub Actions `project-control` Job，仅对 PR -> main 执行，后续 main Ruleset 将要求该 Check。
- 新增 PR Template，提示 Definition of Done 与项目控制同步项。
- 新增无第三方依赖的自动检查脚本及单元测试。
- 将 Project Control 纳入硬性 Definition of Done。

未修改业务代码、数据库 Schema、Alembic Migration 或 Supplier/Product/Quote 冻结规则。
