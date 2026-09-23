# 自由推品 Recommendation

状态：B_CORE_C_AGENT_WEB_INTEGRATED / EXPORT_PENDING

- 统一 Bid Project 类型、自由推品创建合同、模板版本和字段映射 API 已由 `20260923_0039` 提供。
- B 已实现 Run、确定性商品/类目检索、候选快照、人工确认及受权限保护的独立 Router；Router 已注册到 API V1，C Agent 已通过 B Application Service 接入。
- 商品检索固定过滤 `ACTIVE` 商品、已归档且正常合作的未删除供应商；毛利率、京东价和品牌/类目条件只接受经 Pydantic 校验的结构化需求，不允许 AI 直连正式业务库。
- 候选确认时会再次验证商品和供应商当前可用；确认记录存在即代表该候选可进入后续导出，未确认候选不应导出。
- 导出尚未实现：现有 Schema 缺少“导出文件记录”及“厂家直供人工确认”字段，B 已提出 Migration Requirement，等待 A 评审后再接入。
- C 已实现 DeepSeek 适配器、严格结构化解析、受控 AgentRunner、任务 Job 入口和类型4 Web 页面；本机 Inline 模式创建 Run 后直接执行 Agent，DeepSeek 未配置时 Run 进入 `FAILED` 并返回安全提示。
- 模板映射须经人工 PATCH 确认；模板文件按 `RECOMMENDATION_TEMPLATE` 递增版本保留。
- FILTER 携带自由推品模板会被拒绝；PATCH 会校验已保存工作簿的 sheet、行号和源表头。
- Agent 最多调用 8 次受控工具，Provider 失败只重试 1 次；模型不能生成 SQL，也不能返回工具未提供的类目或商品 ID。
- 自由推品未指定类目、品牌、预算、价格或数量时按开放条件处理；仅需求不可执行、硬条件矛盾或存在必须人工决策的合规问题才进入 `NEEDS_INPUT`。页面支持补充说明后创建新 Run，并展示每次实际读取的需求快照。
- Web 已支持类型1–3/类型4创建分流、类型5禁用、映射确认、运行状态、候选理由和人工确认，并已对齐 B 的 `/recommendation-projects` 合同。导出按钮保持禁用，等待 A 评审 B 提出的导出 Migration Requirement。
- Web 人工确认固定刷新当前 Run，并提供 Run 历史切换，后续失败 Run 不再覆盖当前成功候选；候选支持逐条确认和最多 30 条原子批量确认，复用 `recommendation:review`。
