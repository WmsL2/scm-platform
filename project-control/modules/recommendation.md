# 自由推品 Recommendation

状态：B_CORE_AND_C_AGENT_WEB_IMPLEMENTED / INTEGRATION_AND_EXPORT_PENDING

- 统一 Bid Project 类型、自由推品创建合同、模板版本和字段映射 API 已由 `20260923_0039` 提供。
- B 已实现 Run、确定性商品/类目检索、候选快照、人工确认及受权限保护的独立 Router；Router 总聚合与 Agent 执行由 A/C 后续接入。
- 商品检索固定过滤 `ACTIVE` 商品、已归档且正常合作的未删除供应商；毛利率、京东价和品牌/类目条件只接受经 Pydantic 校验的结构化需求，不允许 AI 直连正式业务库。
- 候选确认时会再次验证商品和供应商当前可用；确认记录存在即代表该候选可进入后续导出，未确认候选不应导出。
- 导出尚未实现：现有 Schema 缺少“导出文件记录”及“厂家直供人工确认”字段，B 已提出 Migration Requirement，等待 A 评审后再接入。
- C 已实现 DeepSeek 适配器、严格结构化解析、受控 AgentRunner、任务 Job 入口和类型4 Web 页面；下一步将 Agent 工具与 B Service/Router 对齐。
- 模板映射须经人工 PATCH 确认；模板文件按 `RECOMMENDATION_TEMPLATE` 递增版本保留。
- FILTER 携带自由推品模板会被拒绝；PATCH 会校验已保存工作簿的 sheet、行号和源表头。
- Agent 最多调用 8 次受控工具，Provider 失败只重试 1 次；模型不能生成 SQL，也不能返回工具未提供的类目或商品 ID。
- Web 已支持类型1–3/类型4创建分流、类型5禁用、映射确认、运行进度、候选理由、人工确认和导出入口。除 A 已冻结接口外，推荐运行相关路径集中在 `src/api/recommendation.ts`，等待 B 合并时统一对齐。
