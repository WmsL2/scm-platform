# 智能匹配

状态：IMPLEMENTED / FRONTEND_ACCEPTANCE_PENDING
Owner：投标项目 2 号任务
Last Updated：2026-09-15

## Database
- [x] 匹配任务、候选商品、人工选品历史及需求行当前选品引用已由 `20260915_0024` 创建。

## Backend
- [x] 批量查询 `ACTIVE` Product 与 `ARCHIVED + NORMAL + not deleted` Source Supplier，避免按需求行 N+1 查询。
- [x] 启动匹配通过既有 TaskQueue 抽象在本机 `inline` 模式执行，写入 `scm_match_task`、候选、行级状态和可解释 `match_reason`；每次启动生成独立任务边界。
- [x] 已提供候选列表、人工选品、无法报价和启动匹配四个 API；人工选品重新校验当前 Product/Supplier 状态与需求限价。
- [x] Selection 追加写入需求、商品、供应商、价格快照，再原子更新 `current_selection_id`；重新选品后已导出项目回到 `READY`。

## Frontend
- [ ] 未开始

## Permissions
- [x] 使用 1 号任务提供的 `bid:match`、`bid:select` 和 `bid:detail` 权限。

## Tests
- [x] 领域、DTO、OpenAPI 路由和 MySQL 持久化测试共 20 项通过；Ruff 与 mypy 通过。

## Known Issues
- ARQ 生产任务运行器仍未配置；当前开发环境已使用既有 `inline` TaskQueue 完成真实数据库验收。

## Next Step
交由 3 号任务联调页面；正式启用 ARQ 时补充可跨进程执行的任务 worker 与进度回报验收。
