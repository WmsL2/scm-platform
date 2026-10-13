# Change：修复类型 3 Migration 的 CI Ruff 格式失败

日期：2026-10-13
分支：`codex/feat/type3-sheet-category-selection`

## 问题

类型 3 独立 Migration `20261013_0055` 的 `upgrade` / `downgrade` 调用被压缩为超长单行，GitHub 后端 CI 执行全量 `ruff check .` 时出现 1 个导入分组错误和 8 个 `E501` 超长行错误，导致后续 Mypy、Alembic 和 pytest 未执行。

## 变更

- 按项目 100 字符格式规范等价展开 `create_table`、`create_index`、`drop_index` 调用。
- 修正 Alembic 与 SQLAlchemy 的导入分组。
- 未改动表名、字段类型、外键、索引、唯一约束、检查约束、Revision 依赖以及升级/降级顺序。

## 验证

- `python -m ruff check .`
- `python -m mypy app`
- `python -m alembic heads`，确认单 Head 为 `20261013_0055`
- `python -m pytest -q`

## 影响

- Alembic Revision：无新增，继续使用 `20261013_0055`。
- API / UI / 权限：无变化。
