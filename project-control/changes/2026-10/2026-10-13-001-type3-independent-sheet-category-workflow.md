# 类型 3 独立 Sheet 类目推品

日期：2026-10-13  
状态：IMPLEMENTED / REAL_ACCEPTANCE_PENDING

## 变更

- 新增独立 `type3_recommendation` 模块、API、Run、Sheet 配置、候选与导出记录；不读取或写入类型 4 的 Run、候选、确认或导出表。
- 用户从工作簿候选节点中手工选择一个或多个 Sheet，以及一级、二级或三级类目；不再自动扫描 Excel 并伪造/覆盖备注需求。
- 备注以原文快照保存，由独立 Type-3 Agent 只解析价格、折扣、毛利和强制品牌；人工选择的类目永远是类目边界。
- 后端先按备注硬条件冻结真实商品类目目录，AI 只允许返回目录 key；未匹配节点不扩展到全商品库。
- 商品候选与确认带 `sheet_name`，同一商品可在不同 Sheet 分别确认；导出以原始 Excel 为底稿，只向各来源 Sheet 的映射列写入本 Sheet 已确认候选。
- 类目页采用 Sheet 侧栏 + 当前 Sheet 搜索/分页布局；可按编码或名称搜索，并全选当前页，已选节点跨分页保留。
- 自动识别范围固定为所选 Sheet 的前 120 行、前 40 列；页面明确展示此范围。每个 Sheet 可手工补充最多 50 个一级、二级或三级类目，加入后自动勾选并进入同一受控类目映射流程。
- “保存人工选择”新增独立读取链路：刷新或重新进入页面会回显已保存 Sheet、勾选节点和手工节点；手工节点显示为可关闭标签，移除会同步取消勾选，支持保存空选择以清空已保存配置。
- 类型 3 在项目处于 `SELECTING` 时重新生成候选保持当前状态，不再错误请求 `SELECTING -> MATCHING` 的非法状态回退；审计事件如实记录状态未变的重跑。
- 生成请求执行中会忽略重复点击，同文案错误提示合并显示，避免一次操作出现多条相同提示。
- 候选商品快照中的 Python `date` 与 `datetime` 都在写入 JSON 前转换为 ISO 字符串；Run 创建、内联 AI 执行及结果读取各自使用独立事务。执行器读取 Run 后会结束 SQLAlchemy 隐式只读事务，候选持久化或 AI 异常能安全把既已提交的 Run 标记为 `FAILED`，不会再让 Run 停在 `QUEUED` 或由已关闭事务造成 HTTP 500。
- 新增 `GET /api/v1/type3-recommendation-projects/{project_id}/sheet-selections`，使用既有 `recommendation:detail` 权限；不影响类型 4 合同。

## 数据库

- Alembic：`20261013_0055`，基于 `20261012_0054`。
- 新表：`scm_type3_sheet_config`、`scm_type3_recommendation_run`、`scm_type3_recommendation_candidate`、`scm_type3_recommendation_export`。

## 验证

- `ruff check app/modules/type3_recommendation app/modules/bid/application/service.py app/api/v1/router.py`：通过。
- `mypy app/modules/type3_recommendation`：通过。
- `pytest tests/recommendation/test_template_contracts.py -q`：12 passed。
- `alembic heads`：单 Head `20261013_0055`。
- 前端 `npm run typecheck`、`npm run build`：通过。
- 后端 `ruff check app/modules/type3_recommendation app/modules/bid/application/service.py app/api/v1/router.py`、`mypy app/modules/type3_recommendation`：通过。
- `pytest tests/recommendation/test_type3_candidate_snapshot.py -q`：通过，覆盖日期快照 JSON 序列化。
- `pytest tests/recommendation/test_type3_agent.py -q`：通过，覆盖读取 Run 后关闭隐式只读事务。

## 未完成

- 需在开发库执行 Migration，并使用真实 DeepSeek 与浏览器/WPS 对多 Sheet 工作簿完成端到端验收（包括刷新回显、手工节点移除及 `SELECTING` 状态重跑）。
