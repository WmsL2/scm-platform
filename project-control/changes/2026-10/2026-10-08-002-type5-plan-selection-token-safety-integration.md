# Change Record：类型 5 Token 安全与方案选择持久化兼容

日期：2026-10-08
分支：`codex/fix/type5-token-safety`

## 兼容整合

- 保留 Token 安全链路：完整候选池冻结、短 ID 有界窗口、最多 12 个 AI 核心商品、后端严格补齐至每方案配置数量、Run 冻结配置、逐档短事务状态和仅补缺失槽位的重试。
- 同时恢复方案选择持久化：`PptSolutionPlan.is_selected`、`selected_by`、`selected_at`，以及 `POST /api/v1/ppt-solution-projects/plans/{plan_id}/select`（`recommendation:review`）。选择方案在一个短事务中确认其冻结候选并写入选择审计；后续重试不会修改已存在方案或其选择状态。
- `ppt-v8` 作为受控类目路径处理，不会错误套用早期语义类目过滤；选择方案的回归测试覆盖其人工确认。

## 数据库

- `20261008_0047`：保留 main 的方案选择字段 DDL。
- `20261008_0048`：保留逐价格档生成状态表及 `(run_id, price_band_index)` 唯一约束。
- `20261008_0049`：保留 Run 的 `ppt_config_snapshot` JSON 字段。
- `20261008_0050`：仅以 `0047`、`0049` 为双父 revision 合并迁移图，不新增 DDL，避免改写已在开发库应用的 `0049` 历史。

## 验证边界

- 本机开发库从 `20261008_0049` 执行 `alembic upgrade head`，成功到 `20261008_0050`。
- MySQL HTTP 集成测试覆盖部分失败、并发重试、500 件精确补齐，并新增方案选择在新 Session 中可读取且重试后保持不变的断言。
- Catalog 的全库无筛选 selection-ids 测试在本机大数据开发库会触发既有 5,000 条业务上限；应由独立 Catalog 测试改为限定其自建供应商，而不是放宽业务限制。

## 本轮结果

- `ruff check .`、`mypy app` 通过。
- `pytest tests/recommendation -q`：66 passed；其中真实 MySQL HTTP 专项：2 passed。
- `pytest -q`：283 passed、1 failed；唯一失败为本机开发库中 `test_product_selection_ids_reuses_active_supplier_visibility` 未传筛选条件而触发 `PRODUCT_EXPORT_SELECTION_LIMIT_EXCEEDED`，不修改 Catalog 业务上限。
- Web：Vitest 165 passed、typecheck 通过、production build 通过。
