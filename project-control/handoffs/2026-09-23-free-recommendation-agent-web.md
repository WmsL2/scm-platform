# Handoff：自由推品 Agent/Web（C → B/A5）

## C 已完成

- `app/integrations/deepseek/`：真实 Provider 适配与结构化输出校验。
- `app/modules/recommendation/application/agent_runner.py`：受控 Agent 编排。
- `app/jobs/recommendation_agent.py`：队列兼容 Job 与 B 持久化 Port。
- `apps/web-admin/src/views/bid/RecommendationWorkspaceView.vue`：类型4工作台。
- 类型4项目创建和 A 模板映射 API 已接通。

## B 对接结果

1. `RecommendationServiceTools` 已将 AgentRunner 对接 B 的类目池和商品检索，只返回受控商品投影。
2. `RecommendationServiceJobPort` 已通过 B Service 保存结构化需求、类目选择、候选、失败和取消状态。
3. 前端已对齐 Run 列表/创建、候选和确认接口；取消与导出因 B 尚未提供而不发起请求。
4. B 保存 Agent 结果前继续重新校验 Product ID、价格和商品状态，并生成不可变快照。
5. 人工确认后前端固定刷新原 Run，并提供历史 Run 选择；新增批量确认 API，可一次原子确认最多 30 个属于同一 Run 的候选。

## A5 对接点

- B Router 已注册到 API V1；C 在 create Run 后调用 Inline Agent 集成入口。
- 正式 ARQ 模式仍由基础设施适配器提供依赖实例，业务代码不直接依赖 Redis。

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
