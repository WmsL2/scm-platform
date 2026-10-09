# Change Record：类型 5 价格档直接 AI 匹配与勾选确认

日期：2026-10-09
分支：`codex/feat/type5-direct-band-selection`

## 变更

- 价格档新增逐档 `item_count`，配置页面移除“每个方案商品数量”和“每档生成方案数”。
- 每档 AI 只匹配一次，后端用同档冻结候选补齐或截断到该档指定数量；新 Run 删除未入选的冻结候选，只将实际匹配商品展示给人工确认。
- 类型 5 工作台移除方案卡、方案详情、选方案和重试方案入口，改为与类型 4 一致的候选商品表：图片、SKU、商品名称、可自定义列、分页、复选和批量确认。
- 候选表复用类型 4 的服务端“全选全部待确认”确认合同；跨页取消的商品以排除清单提交，无需将全部候选 ID 传给浏览器。分页支持每页 50 / 100 / 200 条、跳页和页码切换。
- 类型 5 配置界面移除“混合推品”选项；既有历史配置继续按其冻结值读取，不做数据迁移。
- 多价格档结果统一展示；价格档不允许重叠，避免同一商品重复占用不同档位的数量。
- 历史冻结快照仍以原 `PLANS` 模式生成/读取方案卡；新配置快照使用 `DIRECT`，两种历史数据不互相覆盖。

## 数据库 / 接口

- 无 Alembic Migration、无新增表。
- 类型 5 配置请求/响应的 `price_bands[]` 新增必填 `item_count`；移除新配置中的全局 `candidate_count_per_band` 和 `plan_count_per_band`。
- 权限不变：生成使用 `recommendation:run`，人工勾选确认使用 `recommendation:review`。

## 验证

- `pytest tests/recommendation -q`：70 passed。
- MySQL HTTP 类型 5 专项：2 passed，覆盖新直接匹配 Run 精确保留 500 件同档冻结候选且不创建方案卡记录。
- Ruff、Mypy：通过。
- 前端：`npm run typecheck`、全量 Vitest（165 passed）和 production build：通过。
