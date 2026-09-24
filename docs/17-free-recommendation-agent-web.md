# 类型4自由推品 Agent 与 Web

## 1. 使用流程

1. 在投标与推品项目页面选择“类型4 · 自由推品 Agent”。
2. 填写项目、需求方和不少于 20 字的场景需求说明。
3. 上传本项目的推荐结果 `.xlsx` 模板。
4. 创建后确认工作表、表头行、数据起始行和模板字段映射。左侧展示上传模板的真实列名且不可修改，右侧从商品主数据字段中搜索选择要写入的数据。
5. 启动 Agent，查看需求理解、类目方向、候选排序和推荐理由。
6. 运营人员确认候选的活动价、履约说明和依据。
7. 全部满足服务端确认条件后导出推荐结果。

自由推品允许类目、品牌、价格区间、预算和数量留空；系统会从满足硬性毛利与状态规则的正式商品中探索方向。节日、活动、人群和“特价”等属于场景词，不会错误地当成商品类目过滤。“一件代发”等明确履约信息会进入结构化需求。

当状态为“需要补充信息”时，工作台展示 Agent 本次实际读取的需求快照和问题。运营可在页面填写补充说明并重新生成；系统更新项目备注并创建新的 Run，旧 Run 的需求快照和结果继续保留。

工作台按当前 `run_id` 刷新状态和候选，人工确认后不会自动切换到项目中更新创建的其他 Run。运营可通过运行时间和状态下拉查看历史 Run；重新生成前会提示创建新记录，已有候选和确认结果不会被覆盖。候选既可逐条补充活动价与履约说明，也可勾选最多 30 条后一次原子批量确认。

类型5 PPT 方案在当前阶段仅展示“暂未开放”，不能创建。

映射页会读取当前模板真实的工作表和表头。与商品主数据正式列名相同的列会自动匹配，运营可以搜索并调整；同一个商品字段不能同时映射到两个模板列，重复模板表头也不能确认映射。页面方向虽然显示为“模板列 → 商品字段”，保存时仍使用后端既有的 `商品字段 key -> 模板表头` 合同，现有 Agent 与结果导出流程不受影响。

可选数据源包括商品主数据正式 43 列，以及人工确认的“是否厂直”。新生成候选会冻结这些商品字段和供应商名称，导出使用候选创建时快照，避免商品后来修改导致推荐历史漂移。该功能上线前创建的历史候选没有新增快照字段时，对应导出单元格为空。

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
- 数据库先按既有稳定规则筛选商品；最多 30 个真实候选以确定性 round-robin 跨类目合并后才送入 AI 排序。AI 只能排序这些 ID，最多返回 30 条。
- 每次运行最多调用 8 次受控工具，Provider 失败最多重试一次。
- `CandidateRanking` 只能返回顶层 `candidates` 的 JSON object，每项只含 `product_id`、`score`（0–100）和非空 `reason`。严格 Schema、未知字段、UUID、分数和重复 ID 校验均不放宽。
- 结构化 JSON/Schema 错误会附带脱敏校验位置进行一次纠错重试；第二次仍失败时 Run 安全标记为 FAILED。不会持久化或记录原始 DeepSeek response、完整 Prompt 或候选商品 JSON。
- Agent 不接收 SQL 工具，不接触数据库连接信息，不直接写正式业务库。
- 正式商品状态、价格、确认、快照、审计和导出由后端确定性服务重新校验。

## 4. 前后端对接边界

A 已冻结的项目创建与模板映射接口直接使用。B 已提供的 Run、详情、候选、逐条确认和批量确认接口均通过前端 `src/api/recommendation.ts` 调用，完整前缀为 `/api/v1/recommendation-projects`。批量确认由服务端在一个事务中重新校验全部候选的商品和供应商状态，任何一项失效都会整批拒绝。

模板映射工作台通过 `GET /api/v1/bid-projects/{project_id}/recommendation-templates/{file_id}/structure` 按所选 Sheet 和表头行读取真实列结构；该接口复用 `recommendation:create` 权限，只读取已保存且摘要校验通过的项目模板。

后端 Job 通过 `RecommendationServiceJobPort` 与 B 的持久化服务对接；AgentRunner 通过 `RecommendationServiceTools` 查询真实类目和商品。C 不依赖 B 的 Repository，也不直接访问数据库。

当前本机 `TASK_MODE=inline` 时，创建 Run 的请求会等待 Agent 完成，前端超时为 5 分钟。正式 ARQ 后台执行仍需基础设施适配；取消接口尚未开放。

确认结果导出由 `20260923_0040` 提供：Run 必须处于 `CONFIRMED` 或 `EXPORTED`，且至少存在一条人工确认候选。导出仅写入已确认候选，保留当前已确认推荐模板的格式、公式和字段映射；每次生成独立 `RECOMMENDATION_EXPORT` 附件及导出审计记录。人工确认可填写“是否厂直”三态（待确认／是／否），系统和 AI 不推断该值。导出和下载均要求 `recommendation:export`；下载文件名按 UTF-8 标准编码，支持中文名称。
