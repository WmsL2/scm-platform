# Change Record：推荐 Run 历史加载索引修复

日期：2026-10-12
模块：recommendation
分支：`codex/fix/ppt-run-history-load`

## 问题

类型 5 工作台点击项目时按 `project_id` 查询 Run 历史并按 `created_at DESC` 排序。原表仅有单列索引；包含较大 JSON 快照的历史行会触发 MySQL `filesort`，在较小 `sort_buffer_size` 下报 1038，接口返回 500。

## 本次变更

- 新增 `scm_recommendation_run(project_id, created_at)` 复合索引。
- 保持 Repository、API、前端请求与类型 1--5 业务规则不变。
- 新增 ORM 索引声明回归测试。

## 数据库

- Alembic Revision：`20261012_0053`。

## 验证

- `pytest tests/recommendation/test_recommendation_run_history_index.py -q`：1 passed。
- `ruff check app/modules/recommendation/infrastructure/models.py alembic/versions/20261012_0053_recommendation_run_history_index.py tests/recommendation/test_recommendation_run_history_index.py`：通过。
- `mypy app/modules/recommendation/infrastructure/models.py`：通过。
- `python -m alembic upgrade head`：开发库已到 `20261012_0053 (head)`。
- 对问题项目历史 Run 查询执行 `EXPLAIN`：使用新复合索引和 `Backward index scan`，不再出现 `Using filesort`。
