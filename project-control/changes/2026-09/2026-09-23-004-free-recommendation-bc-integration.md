# Change Record：自由推品 B/C 第一轮集成

日期：2026-09-23  
模块：recommendation / web-admin

## 原因

板块 B 合入后独立 Router 尚未注册，C 前端仍调用临时 `/api/v1/recommendations` 合同，导致模板映射成功后创建 Run 返回 404。

## 修改

- 将 B `recommendation_router` 注册到 API V1。
- 前端统一改用 `/api/v1/recommendation-projects` 的 Run、候选和确认合同。
- 前端详情将 Run 列表和候选列表组合成工作台视图；不再请求尚不存在的取消和导出接口。
- 新增 `RecommendationServiceTools` 与 `RecommendationServiceJobPort`，Agent 仅通过 B Application Service 读取真实类目/商品并持久化结果。
- Inline 模式创建 Run 后执行 DeepSeek Agent；未配置 Key 或 Provider 失败时写入脱敏失败信息。
- 固定最低毛利率默认值为 6%，仍由 B 的确定性商品检索执行。
- 自由推品的类目、品牌、价格、预算和数量为可选探索条件；未提供或写明“暂无”不再自动触发 `NEEDS_INPUT`。节日/活动关键词不作为类目硬过滤，一件代发保存为履约方式。
- 工作台展示本次 Agent 实际读取的不可变需求快照；确需补充时可填写说明、更新项目备注并创建新 Run，旧 Run 不覆盖。
- 导出按钮继续展示但禁用，等待专用导出 Schema 与厂家直供人工确认字段。
- 修复人工确认后的 Run 串台：前端按当前 Run ID 获取状态与候选，不再在每次刷新时重新选择项目最新 Run。
- 增加运行历史下拉和重新生成确认提示，成功候选与确认记录可继续查看。
- 增加最多 30 条候选的原子批量确认接口和前端多选操作；全部候选在同一事务内重新校验商品与供应商有效性。

## 数据库/API/权限

- Alembic Revision：无。
- 新增注册的 API 前缀：`/api/v1/recommendation-projects`。
- 新增 API：`POST /api/v1/recommendation-projects/runs/{run_id}/confirmations`。
- 权限不变，复用 `recommendation:run/detail/review`。
- 未新增取消或导出 API。
