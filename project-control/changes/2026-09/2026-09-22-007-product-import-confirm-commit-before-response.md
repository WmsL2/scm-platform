# 2026-09-22-007：商品 Import Confirm 在响应前提交

- FastAPI 运行版本为 0.141.1。仅 `POST /products/imports/{task_id}/confirm` 使用 function-scoped request transaction，使 yield dependency 在 HTTP response 发送前退出并 commit。
- Confirm 专用认证依赖与 route 共享同一个 function-scoped `AsyncSession`；Service 继续只参与 caller-owned transaction、只 flush，不自行 commit，符合 ADR-0007。
- 前端不变；Confirm 成功后的既有 Product List 刷新会在 HTTP 200 后立即读取已提交数据。
- Alembic Revision、API payload、Permission：无变化。
