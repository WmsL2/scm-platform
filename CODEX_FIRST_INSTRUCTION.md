# 给 Codex 的第一条指令

请完整阅读并执行：

`prompts/00-create-project-foundation.md`

这是一个新项目，请从零建立 Sprint 0 企业级工程底座。

必须严格遵守：

- `AGENTS.md`
- `project-control/`
- 全部已 ACCEPTED ADR

这是 Local-First 项目：

- 不要求 Docker；
- 后端唯一使用 FastAPI；
- 数据库使用 MySQL 8；
- Sprint 0 不开发具体业务模块；
- Sprint 0 不创建全量业务表；
- 商品大表是正式商品主数据；
- 大表一行 = 一条具体商品；
- 一期不强制 SPU/SKU；
- 开发结束必须同步项目文档和执行状态。

直接开始执行，不需要再次设计新的技术栈。
