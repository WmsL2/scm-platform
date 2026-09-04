# Auth/RBAC

状态：BACKEND MERGED / FRONTEND IMPLEMENTED / REAL API VERIFICATION PENDING

## Backend

- 数据库：五张 Auth/RBAC 表，Revision `20260903_0002`。
- API：login、me、logout。
- 权限：CurrentUser、get_current_user、require_permission。
- 安全：Argon2id、HS256、token_version。
- Merge：PR #6 已合入 `main`（Merge Commit `6f229e75`）；实现提交 `d90d519`，CI 修复提交 `066e4df`。
- 测试：Auth Kernel 合入时 30 passed，Warnings 0；Ruff PASS，mypy PASS。

## Frontend

- 实现分支：`feat/web-admin-auth-shell`。
- [x] 登录页面和表单校验。
- [x] Pinia Auth Store、Token 持久化和刷新恢复。
- [x] login、me、logout API 封装。
- [x] 本地开发 Mock / 真实 FastAPI 配置切换，生产构建强制关闭 Mock，页面明确展示当前模式。
- [x] 路由登录守卫、权限码守卫、401/403 统一处理。
- [x] 企业后台 Layout、工作台、工作区 Tab、403、404。
- [x] HTTP GET/POST/PATCH/DELETE、request ID、Bearer Token 和统一错误处理。
- [x] 前端单元测试、typecheck 和 build。

## Boundaries

- Mock 仅在 Vite 开发模式下可启用，用于后端开发库不可用时的前端验收；生产构建始终调用真实 API，Mock 不代表真实接口联调通过。
- 工作台无可信接口的数据保持 `--`，不填充虚构统计值。
- 未创建供应商业务表单，Supplier Field Gate 保持有效。
- 前端权限只控制路由和显示，后端 `require_permission` 仍是安全边界。

## Pending

- 使用迁移完整的 MySQL 开发库完成 login/me/logout 真实接口联调。
- Refresh Token、Session、Multi-device Logout。
- Business Sequence 由后端任务继续推进。

## Next Step

数据库基线恢复后切换 `VITE_USE_MOCK=false` 做真实接口验收；Supplier Gate 保持有效。
