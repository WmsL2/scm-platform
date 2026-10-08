# Change Record：类型 5 方案合同重试与失败可见性

日期：2026-10-08
分支：`codex/fix/type5-plan-contract-fallback`

## 问题

- 某个价格档的完整候选池和可用数量都已冻结且满足配置时，DeepSeek 仍可能返回少于
  配置数量的方案、重复方案编号，或窗口之外的短 ID。
- 原实现只会重试 JSON Schema 解析失败；上述已解析但不完整的方案合同错误会进入服务层的
  通用异常分支，页面最终只显示 `AppError` 与“方案生成失败”，无法区分候选不足和模型输出异常。

## 变更

- 在每个价格档的模型响应进入持久化前，校验返回的 `(price_band_index, plan_no)` 必须与该档
  配置的全部方案槽位精确一致且不重复，并继续校验所有短 ID 均来自当前 AI 窗口。
- 对 JSON Schema 错误和上述安全方案合同错误均只自动重试一次；重试提示只包含脱敏的合同原因，
  不包含候选 JSON、原始模型响应或密钥。
- 当模型返回的合法核心短 ID 数超过当前“每方案商品数量”时，服务端只保留前 N 个核心偏好；
  不再把已满足商品池的价格档误报为“商品不足”。
- 两次失败后，将安全原因写入逐档生成状态；异步任务适配器将 `AppError.message` 显示为可操作的
  类型 5 失败说明，不再将其压缩为泛化的 `(AppError)`。

## 数据库 / 接口

- 无 Alembic Migration。
- 无路由、请求/响应字段、权限变化；既有逐档 `error` 字段的值由泛化文案提升为安全具体原因。

## 验证

- `pytest tests/recommendation/test_ppt_plan_runner.py`：5 passed，覆盖不完整方案槽位的纠错重试。
- `pytest tests/recommendation/test_type5_mysql_http_integration.py`：2 passed。
- `pytest tests/recommendation -q`：70 passed。
- `ruff check`（本次 4 个 Python 文件）：通过。
- 使用失败 Run 的冻结候选进行只读真实 DeepSeek 探测：100 元档 111 件候选、配置 3 套 × 10 件，
  当前模型可返回 3 个有效槽位；这说明候选数量不是该次失败原因。真实页面重新生成验收仍待执行。
