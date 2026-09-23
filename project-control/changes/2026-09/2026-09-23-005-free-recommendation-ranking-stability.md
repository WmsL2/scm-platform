# Change Record：自由推品候选排序稳定性

日期：2026-09-23  
分支：`fix/recommendation-ranking-stability`

## 变更

- 将 CandidateRanking 的输入、严格 Schema 输出和持久化上限统一为 30 条。
- 多个类目检索结果按 Repository 已有稳定顺序，以确定性 round-robin 去重合并；不使用随机抽样，首个类目不会独占全部名额。
- 新增 `DeepSeekStructuredOutputError`，只携带 response model、错误类别及不含 Pydantic 输入值的 `loc/type/msg` 摘要。
- 结构化失败仅自动带脱敏纠错提示重试一次；Job 按阶段记录安全用户文案和脱敏日志，不保存原始 Provider 响应、完整 Prompt 或候选 JSON。

## 验证

- 5 类目 × 20 商品的测试确认 Provider 排序输入不超过 30，结果和持久化不超过 30，且 ID 全部来自受控候选。
- 覆盖非法 JSON、缺字段、超范围分数、未知字段、超过 30 条、首次结构错误后成功及连续失败的安全 FAILED 文案。

## Migration

无。`record_progress()` 的 no-op 仍为既有技术债，本次未扩大为 Schema 变更。
