# Change Record：类型 5 独立 V8 受控选品与方案 AI

日期：2026-09-30  
分支：`codex/feat/type5-reuse-v8-selection`

## 变更

- 类型 5 新增独立的 Catalog Service、Repository、需求/类目 Runner 与 Adapter；不调用类型 4 的选品 Service 或 Repository。
- 类型 5 复制 V8 业务规则：先按正式商品和供应商状态及数值硬条件筛选，再冻结一级、二级、三级真实类目目录；AI 只能返回本次目录的 key，父级选择展开子路径。
- 类型 5 在不叠加价格档的完整候选池冻结后，使用独立方案 AI 按价格档仅从已冻结 `candidate_id` 组织方案；后端校验方案槽位、商品数量、价格档和未知 ID。
- 推品配置不再拼接进首轮客户需求 Prompt，避免价格档或方案数量反向缩窄与类型 4 同口径的候选召回；配置仅提供给后续方案 AI。
- 方案编排失败不会删除已冻结候选池；页面仍可展示候选统计和人工选品状态。
- 移除“完整候选池超过 1,000 件即失败”的限制：方案 AI 按价格档分别编排，只接收该档候选；当前单档技术传输上限为 5,000 件，3543 件完整候选不会再被总数拦截。
- 新增价格档可用性只读接口。页面展示每档按协议价计算的真实冻结候选数、每方案要求数量及是否可生成，避免无方案时误报为“商品数量不足”。

## 数据库

- Revision `20260930_0046` 为 `scm_ppt_solution_plan` 新增 `selection_source`、`selection_provider`、`selection_model`、`selection_prompt_version`，记录方案来源与 AI 审计信息。

## 边界

- 类型 4 的 Runner、Repository、候选表、Excel 导出和 API 合同不改。
- 类型 5 仅共享 Run、Candidate、Confirmation 等基础数据模型及事务/权限基础设施；选品业务逻辑与 PPT 方案链路独立维护。
- 真实 DeepSeek 和浏览器端到端验收仍待执行。
