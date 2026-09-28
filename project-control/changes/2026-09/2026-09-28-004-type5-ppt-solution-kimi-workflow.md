# 2026-09-28 类型 5 PPT 方案首版

## 完成

- 开放类型 5 项目创建，支持填写甲方需求及可选上传客户 PPTX 模板。
- 新增 Kimi 结构化选品适配器，模型只能从商品主数据受控候选中返回最多 30 条推荐。
- 新增独立 PPT 方案工作台：AI 推荐在左、人工已选在右，支持单条/批量确认、移除和返回调整。
- 新增人工套装，支持商品数量、价格档位和组套说明，并阻止套装总价超过档位。
- 新增 Kimi Hosted PPT Agent 生成任务、客户模板/默认模板分流、PPTX 版本保存和下载。
- PPT 生成文件可沿用项目提交及中标/未中标状态流程。

## 数据库与接口

- Alembic Revision：`20260928_0041`。
- 新增表：`scm_ppt_solution_package`、`scm_ppt_solution_package_item`、`scm_ppt_generation_task`。
- 新增文件类型：`PPT_TEMPLATE`、`PPT_EXPORT`。
- 新增 `/api/v1/ppt-solution-projects` 下的套装、生成记录和下载 API。
- 权限复用 `recommendation:detail`、`recommendation:review`、`recommendation:export`，无新增权限码。

## 验证

- Ruff、Mypy 通过。
- 后端全量：269 passed；recommendation/bid/foundation 定向回归：61 passed。
- Web 类型检查、159 个 Vitest、生产构建通过。
- 真实 Kimi Hosted Agent 尚待企业凭据联调。
