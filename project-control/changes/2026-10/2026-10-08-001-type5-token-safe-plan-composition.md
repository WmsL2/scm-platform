# Change Record：类型 5 Token 安全方案编排与失败恢复

日期：2026-10-08
分支：`codex/fix/type5-token-safety`

## 根因

- 旧实现会把单一价格档最多 5,000 件候选及其真实 UUID 全量发送给模型；商品数量不是 Token 预算。
- 旧协议要求模型返回每个方案完整 UUID 数组；`500 件 × 20 方案` 的理论输出远超默认 `DEEPSEEK_MAX_TOKENS=4096`。
- 客户端没有按 `finish_reason` 区分截断，方案全部完成后才统一持久化，页面也无法精确表达部分成功。

## 变更

- 保留完整冻结候选池；按类目和品牌 round-robin 构造受 `PPT_AI_INPUT_TOKEN_BUDGET` 约束的短 ID AI 窗口，避免固定取前 N 件。
- AI 仅返回每方案有限的 `candidate_keys` 核心商品；服务端依据完整冻结价格档候选补齐到配置的商品数，且只接受窗口内 key。
- 方案按价格档独立调用、校验和事务提交；已有 `(run_id, price_band_index, plan_no)` 不重复写入，后续失败不回滚成功档。
- DeepSeek 记录安全 usage 元数据并区分输出截断、上下文超限、超时及 HTTP 状态；不记录 Prompt、原始响应或密钥。
- 类型 5 类目目录按相同预算完整分批匹配并去重归并。
- 类型 5 首次推品改为独立短 Session 编排：Run 与冻结配置、需求与类目快照、候选池、每个价格档方案状态分别提交；外部 AI 调用期间不复用 HTTP 请求事务，也不持有行锁。类型 4 仍沿用原请求事务路径。
- API 返回每档已生成/请求方案数及失败原因；页面明确显示候选池、成功、部分成功或失败。

## 数据库 / 接口

- Alembic Revision：`20261008_0048`，新增 `scm_ppt_plan_generation_status`，按 Run + 价格档持久化已生成方案数、目标数及安全失败原因；刷新与进程重启后可恢复准确状态。
- Alembic Revision：`20261008_0049`，在 Run 保存经 Schema 校验的类型 5 配置快照；历史 Run 缺失快照时明确拒绝重试，不混用当前项目配置。
- `GET /ppt-solution-projects/runs/{run_id}/plan-availability` 新增每档生成进度和安全失败信息；权限不变。
- `POST /ppt-solution-projects/runs/{run_id}/commands/retry-plans` 仅补齐当前 Run 缺失槽位，权限为 `recommendation:run`。

## 验证

- `ruff check .`、`mypy app`：通过。
- `pytest tests/recommendation -q`：65 passed。
- 本机 MySQL HTTP 专项：2 passed，覆盖首次 Run、跨 Session 持久化、三档部分失败、并发与重复重试、冻结配置及 500 件后端补齐；真实 DeepSeek 联调仍待执行。
- Web 全量 Vitest：165 passed；`vue-tsc` 和 production build：通过。
- 全量后端 pytest 发现 1 项既有 Catalog API 回归：`test_product_selection_ids_reuses_active_supplier_visibility` 返回 422（与本次类型 5 变更无关）。
