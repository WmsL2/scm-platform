# Change Record：自由推品 Requirement V2 与人工核验

日期：2026-09-24
分支：`feat/free-recommendation-requirement-v2`（基于最新 main）

## 变更

- 解析合同区分明确类目、必选/偏好/排除品牌、场景意图、关键词、特价偏好、数量和人工核验；未指定毛利不再默认 6%。
- Repository 对明确类目、必选品牌、排除类目/品牌执行 SQL 硬过滤；关键词与偏好品牌进入稳定候选 bucket，并保留同类目 fallback，不再以毛利率倒序主导候选池。
- 候选 `manual_flags.checks` 复用既有 JSON 存储。新增 review API；确认和批量确认会拒绝必填 `PENDING`/`FAIL` 项。
- Web 工作台显示、编辑并保存人工核验；服务端 409 继续由统一错误提示展示。
- 结果模板新增受控派生字段 `supports_jd_or_sf`，并增加“毛利→profit”等无歧义 Alias。
- 提交前终审补充确认后的核验降级锁、导出的防御性二次核验、SQL NULL 安全排除和物流否定表达保护。

## Migration

无。复用 `RecommendationRun.parsed_requirement` 和 `RecommendationCandidate.manual_flags` JSON，以及既有冻结商品快照。

## 验证

- `ruff check app/modules/recommendation`
- `mypy app/modules/recommendation`
- `pytest -q tests/recommendation`（41 passed）
- 前端 `npm run typecheck`

## 前端行为测试补充

- 新增 `@vue/test-utils` 最小开发依赖，并为 `RecommendationWorkspaceView` 添加真实组件挂载测试。
- 覆盖人工核验渲染、PASS 与依据保存、未完成核验的前端确认拦截、409 业务提示、历史 Candidate/ParsedRequirement 和当前 UI 已展示的 V2 字段。
- 候选列表明确标识必填核验并汇总“未完成／未通过／已完成”；未通过必填核验的候选不能勾选批量确认。
- 单品“确认保存”会先持久化本地人工核验，再提交 Confirmation；批量确认保留前端二次检查和后端最终门禁。
