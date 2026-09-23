# Change Record：自由推品确认结果导出

日期：2026-09-23  
模块：recommendation / bid / web-admin

## 原因

类型 4 自由推品页面此前只能确认候选，导出按钮永久禁用。普通投标报价导出依赖需求行和报价状态，不能正确表达自由推品候选及人工“是否厂直”结论。

## 修改

- 增加 `RecommendationExportService`：从已确认候选快照生成 Excel、保存对象、创建附件、导出审计记录和项目操作事件，并提供受限下载。
- 保留上传模板的工作表、标题、样式、数据起始行及公式行；针对每次导出再次校验工作表和已确认表头映射。
- 在人工确认表增加 `factory_direct` 三态字段；单条确认可填写，批量确认保持 `PENDING`，导出写入“待确认 / 是 / 否”。
- Web 工作台在存在确认候选、Run 为 `CONFIRMED` 或 `EXPORTED` 且用户拥有 `recommendation:export` 时允许导出并自动下载。
- 导出文件使用专用 `RECOMMENDATION_EXPORT` 类型；项目内版本号递增，不能通过普通附件下载接口绕过 Run 归属校验。
- 下载响应头采用 RFC 5987 `filename*` UTF-8 编码，并提供 ASCII 回退文件名，避免中文导出文件名被 Starlette 的 Latin-1 响应头编码拒绝。

## 数据库/API/权限

- Alembic Revision：`20260923_0040`（依赖 `20260923_0039`）。
- 新增表：`scm_recommendation_export`。
- 新增字段：`scm_recommendation_confirmation.factory_direct`。
- 新增 API：`POST /api/v1/recommendation-projects/{project_id}/runs/{run_id}/exports`、`GET /api/v1/recommendation-projects/runs/{run_id}/exports/{file_id}/download`。
- 权限：复用 `recommendation:export`，无新增权限。

## 验证

- `alembic upgrade head` 已在本机 MySQL 通过，当前 Revision 为 `20260923_0040`。
- 后端推荐模块测试覆盖模板保留、字段填充、厂直标签、下载归属和连续版本号。
- 前端类型检查、Vitest 和生产构建已执行；浏览器真实导出验收仍需具有 `recommendation:export` 的账号和实际确认 Run。
