# 自由推品 Recommendation

状态：C_AGENT_WEB_IMPLEMENTED / B_API_INTEGRATION_PENDING

- 统一 Bid Project 类型、自由推品创建合同、模板版本和字段映射 API 已由 `20260923_0039` 提供。
- Run、类目选择、候选、人工确认表仍等待 B 的 Repository/Service/API；C 已实现 DeepSeek 适配器、严格结构化解析、受控 AgentRunner、任务 Job 入口和类型4 Web 页面。
- 模板映射须经人工 PATCH 确认；模板文件按 `RECOMMENDATION_TEMPLATE` 递增版本保留。
- FILTER 携带自由推品模板会被拒绝；PATCH 会校验已保存工作簿的 sheet、行号和源表头。
- Agent 最多调用 8 次受控工具，Provider 失败只重试 1 次；模型不能生成 SQL，也不能返回工具未提供的类目或商品 ID。
- Web 已支持类型1–3/类型4创建分流、类型5禁用、映射确认、运行进度、候选理由、人工确认和导出入口。除 A 已冻结接口外，推荐运行相关路径集中在 `src/api/recommendation.ts`，等待 B 合并时统一对齐。
