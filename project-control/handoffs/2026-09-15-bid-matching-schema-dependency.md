# Handoff: Task 2 Bid Matching Schema Dependency

状态：WAITING_FOR_TASK_1_SCHEMA

日期：2026-09-15
来源分支：`feat/bid-matching-selection`
接收范围：投标模块 1 号任务 / 2 号任务后续接入

## Already Completed by Task 2

- 纯领域层的确定性召回、评分、状态过滤、排序和可解释 `match_reason`。
- 人工选品和无法报价的 Pydantic 请求 DTO。
- 领域及 DTO 测试共 18 条，Ruff 与 mypy 均通过。

## Required Shared Tables and Fields

Task 2 cannot safely write data until Task 1 supplies the following shared schema:

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

## Required Integration Work After Schema Merge

1. 用批量 Product + Supplier 查询将结果转换为 `MatchableProduct`，避免逐行 N+1。
2. 启动匹配时创建任务边界；同一任务幂等，重跑生成新的任务/版本。
3. 持久化 Top 20 候选与 `match_reason`，并在人工选择时重新校验 Product/Supplier
   当前资格和候选归属。
4. Selection 与 `current_selection_id` 在同一事务更新；无报价记录理由和说明。
5. 接入 `bid:read`、`bid:match`、`bid:select`、`bid:export` 权限，随后提供：
   `start-matching`、候选列表、选择和 no-quote 四个 API。

## Explicit Boundaries

- Task 2 不创建或修改 Alembic Migration，不修改 Product/Supplier 生命周期，不接管
  1 号项目/Excel 基础设施，也不实现 3 号前端页面。
- 当前没有真实 bid API 或数据库写入；不能将领域规则通过视作整条投标流程已完成。
