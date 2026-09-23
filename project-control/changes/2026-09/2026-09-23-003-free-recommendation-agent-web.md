# Change Record：自由推品 Agent 与 Web

日期：2026-09-23  
模块：recommendation / bid / web-admin  
分支：`feat/free-recommendation-agent-web`

## 完成内容

- 新增 OpenAI 兼容的 DeepSeek 适配器，URL、模型、超时、Prompt 版本和 API Key 均由环境变量提供；缺少密钥不影响应用启动。
- DeepSeek 输出必须通过 Pydantic 严格模型校验；Provider 异常对外脱敏，不返回密钥或原始响应内容。
- 新增受控 AgentRunner：需求解析、真实类目选择、商品检索、候选排序；最多 8 次工具调用、一次 Provider 重试，拒绝虚构类目、未知商品 ID 和重复候选 ID。
- 新增队列兼容 Job 入口，通过 Port 读取需求、上报进度、检查取消并保存结果；不越权实现 B 所属持久化。
- 投标项目创建页支持类型1–3、类型4和禁用的类型5；类型4要求至少 20 字需求说明和项目级 `.xlsx` 结果模板。
- 新增类型4工作台，支持模板映射确认、运行状态、需求理解、类目方向、候选理由、人工确认和导出入口。
- B 尚未冻结的推荐运行 API 统一隔离在 `src/api/recommendation.ts`，后续联调不要求页面重写。

## 安全边界

- 模型不连接数据库、不生成或执行 SQL。
- 模型只看到受控类目和候选商品投影，不包含数据库连接、供应商联系方式或完整商品库。
- 正式价格、确认、审计和导出仍由确定性后端服务负责。

## Schema / Permission / API

- Alembic Revision：无，复用 `20260923_0039`。
- 权限：复用 `recommendation:create/run/detail/review/export`，无新增权限。
- A 已冻结的项目创建和模板映射 API 已接入。
- B 推荐运行、详情、取消、确认和导出路径为 C 侧临时适配合同，等待 B 完成后统一校准。

## 验证

- 后端 `ruff check app tests`：通过。
- 后端 `mypy app/integrations app/modules/recommendation/application app/jobs/recommendation_agent.py`：通过。
- 后端 `pytest -q`：239 passed。
- 前端 `npm run test`：134 passed。
- 前端 `npm run typecheck`：通过。
- 前端 `npm run build`：通过。
- 未调用真实 DeepSeek：当前未配置用户 API Key。
- 未做浏览器真实 API 联调：B API 尚未交付。
