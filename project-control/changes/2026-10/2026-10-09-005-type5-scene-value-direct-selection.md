# Change Record：类型 5 场景与性价比直接选品

日期：2026-10-09
分支：`codex/feat/type5-scene-value-selection`

## 变更

- 类型 5 直接选品不再让后端以未评估商品补足数量。每个价格档的完整冻结候选先按受控批次由 AI 逐件评估场景匹配、性价比和综合评分。
- 评分输入包含客户原始需求及其解析场景、商品名称/品牌/型号/类目、规格、卖点、协议价、京东价、折扣率、销量和好评率；AI 只能返回服务端短编号。
- 高分短名单在安全输入预算内由 AI 再选出精确 `item_count` 件。若最终比较无法容纳目标数量，则按全部已完成 AI 综合评分选取前 N 件，不再静默补入未评估商品。
- 类型 5 Run 在裁剪前记录冻结候选总数与各价格档候选数；工作台同时显示“冻结候选池”“每档冻结候选”“AI 最终匹配”和人工已确认数量。
- 首轮全量评分将规格、卖点压缩后按 `PPT_AI_ASSESSMENT_CONCURRENCY=4` 受控并发执行；高分短名单最终精选保留完整相关字段。每批与最终比较记录候选数、输入字符数、重试、耗时及 DeepSeek Token 用量。
- 类型 5 新 Run 立即以 `QUEUED` 响应，响应后交由 TaskQueue abstraction 执行；工作台每 3 秒轮询状态并在 AI 完成后显示候选表。
- 修复冻结池提前展示：直接选品在冻结候选后保持 `RANKING`，前端持续显示匹配中；仅在 AI 已删除未入选候选并写入最终结果后转为待人工确认。因此不会再短暂显示数千条冻结商品或允许其被全选。

## 数据库 / 接口

- 无 Alembic Migration、无新增表。
- `GET /api/v1/recommendation-projects/runs/{run_id}` 新增可选 `ppt_frozen_pool_statistics`；仅类型 5 新 Run 有值。
- `POST /api/v1/recommendation-projects/{project_id}/runs` 的类型 5 调用改为后台执行并先返回 `QUEUED`；类型 4 保持原同步行为。
- 类型 4 的召回、AI 提示词、候选表和接口行为不变；权限不变。

## 验证

- 后端推荐模块全量：72 passed（70 项非 MySQL 模块测试 + 2 项 Type 5 MySQL HTTP 专项）。
- 本次状态时序回归：Type 5 MySQL HTTP 专项 2 passed。
- Ruff、Mypy：通过。
- 前端：类型检查、全量 Vitest 165 passed 和 production build：通过。
