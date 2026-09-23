# 类型4自由推品 Agent 与 Web

## 1. 使用流程

1. 在投标与推品项目页面选择“类型4 · 自由推品 Agent”。
2. 填写项目、需求方和不少于 20 字的场景需求说明。
3. 上传本项目的推荐结果 `.xlsx` 模板。
4. 创建后确认工作表、表头行、数据起始行和模板字段映射。
5. 启动 Agent，查看需求理解、类目方向、候选排序和推荐理由。
6. 运营人员确认候选的活动价、履约说明和依据。
7. 全部满足服务端确认条件后导出推荐结果。

类型5 PPT 方案在当前阶段仅展示“暂未开放”，不能创建。

## 2. DeepSeek 配置

后端通过以下环境变量读取配置，API Key 留给部署人员填写：

```env
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_TIMEOUT_SECONDS=60
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_PROMPT_VERSION=free-recommendation-v1
```

API Key 为空不会阻止后端启动，但不能执行 Agent。错误日志和业务错误不得包含密钥、Provider 原始响应或请求中的敏感信息。

## 3. Agent 安全约束

- 需求解析、类目选择和候选排序均使用严格 Pydantic JSON Schema。
- 类目必须来自 `RecommendationTools.list_categories`。
- 候选 ID 必须来自 `RecommendationTools.search_products`。
- 每次运行最多调用 8 次受控工具，Provider 失败最多重试一次。
- Agent 不接收 SQL 工具，不接触数据库连接信息，不直接写正式业务库。
- 正式商品状态、价格、确认、快照、审计和导出由后端确定性服务重新校验。

## 4. 前后端对接边界

A 已冻结的项目创建与模板映射接口直接使用。B 尚未完成的 Run、详情、取消、确认和导出接口全部封装在前端 `src/api/recommendation.ts`，B 合并时只修改该适配层。

后端 Job 通过 `RecommendationJobPort` 与 B 的持久化服务对接；AgentRunner 通过 `RecommendationTools` 查询真实类目和商品。C 不依赖 B 的 Repository 实现，也不修改 B Router。
