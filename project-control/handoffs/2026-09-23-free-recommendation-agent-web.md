# Handoff：自由推品 Agent/Web（C → B/A5）

## C 已完成

- `app/integrations/deepseek/`：真实 Provider 适配与结构化输出校验。
- `app/modules/recommendation/application/agent_runner.py`：受控 Agent 编排。
- `app/jobs/recommendation_agent.py`：队列兼容 Job 与 B 持久化 Port。
- `apps/web-admin/src/views/bid/RecommendationWorkspaceView.vue`：类型4工作台。
- 类型4项目创建和 A 模板映射 API 已接通。

## B 对接点

1. 为 AgentRunner 提供 `RecommendationTools`：
   - `list_categories(keywords, limit)` 只返回商品主数据中真实存在的三级文本路径；
   - `search_products(request)` 只返回受控 `ProductCandidate` 投影。
2. 为 Job 提供 `RecommendationJobPort`：读取 Run 需求、取消标记、进度、完成、失败和取消持久化。
3. 完成 Run/detail/cancel/confirmation/export 后，对齐前端 `src/api/recommendation.ts`；页面禁止直接增加散落 URL。
4. B 保存 Agent 结果前仍需重新校验 Product ID、价格和商品状态，并生成不可变快照。

## A5 对接点

- B Router 完成后由 A5 注册；C 未修改 B Router 或 API 聚合。
- `TASK_MODE=inline` 可直接 enqueue `execute_recommendation_agent`；ARQ 模式由基础设施适配器提供依赖实例，业务代码不直接依赖 Redis。

## 环境变量

```env
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=60
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_PROMPT_VERSION=free-recommendation-v1
```

密钥不得提交到 Git；留空时系统正常启动，运行 Agent 时明确返回未配置错误。
