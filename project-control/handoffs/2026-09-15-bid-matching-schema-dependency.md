# Handoff: Task 2 Bid Matching Schema Dependency

状态：TASK_2_BACKEND_COMPLETE / FRONTEND_ACCEPTANCE_PENDING

日期：2026-09-15
来源分支：`feat/bid-matching-selection`
接收范围：投标模块 1 号任务 / 2 号任务后续接入

## Already Completed by Task 2

- 纯领域层的确定性召回、评分、状态过滤、排序和可解释 `match_reason`。
- 人工选品和无法报价的 Pydantic 请求 DTO。
- 领域、DTO、路由与 MySQL 持久化测试共 20 条，Ruff 与 mypy 均通过。

## Received Shared Tables and Fields

Task 1 delivered the following shared schema in Migration `20260915_0024`:

- `scm_bid_project`、`scm_bid_project_item`；Item 要有匹配处理状态和
  `current_selection_id`。
- `scm_match_task`：项目、触发者、状态、处理总数/进度、开始与结束时间；同一任务
  重试不得重复创建候选。
- `scm_match_candidate`：`project_item_id`、`product_id`、`supplier_id`、`score`、
  `rank`、`method`、`match_reason` JSON、匹配任务/批次边界和创建时间。
- `scm_bid_item_selection`：追加式 Selection ID、`project_item_id`、候选/商品/供应商
  关联，以及需求、商品、供应商、价格与数量的不可变快照。
- Project Item 的 `current_selection_id` 必须能指向当前 Selection；Selection 改选只
  新增记录，再原子移动该指针。

金额列必须为 Decimal/Numeric，不能使用 Float。外键删除策略需保持正式 Product、
Supplier 和已导出历史的可追溯性，不得级联删除选品快照。

## Completed Integration Work

1. 已用批量 Product + Supplier 查询转换为 `MatchableProduct`，避免逐行 N+1。
2. 已创建独立 Match Task、持久化 Top 20 候选和 `match_reason`。
3. 已在人工选择时重新校验 Product/Supplier 当前资格、候选归属和需求限价。
4. Selection 与 `current_selection_id` 已在同一事务更新；无报价记录理由和说明。
5. 已接入 `bid:detail`、`bid:match`、`bid:select` 并提供四个匹配 API。

## Explicit Boundaries

- Task 2 不创建或修改 Alembic Migration，不修改 Product/Supplier 生命周期，不接管
  1 号项目/Excel 基础设施，也不实现 3 号前端页面。
- MySQL 持久化测试已通过；3 号前端浏览器联调和未来 ARQ worker 验收仍未完成。
