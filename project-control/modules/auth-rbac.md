# Auth/RBAC

状态：BACKEND MERGED / FRONTEND MERGED / REAL API VERIFIED

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
- [x] 开发环境显式设置 `VITE_USE_MOCK=false`，并验证真实 API 路径调用
  `/api/v1/auth/login`、`/me`、`/logout`。

## Boundaries

- Mock 仅在 Vite 开发模式下可启用，用于后端开发库不可用时的前端验收；生产构建始终调用真实 API，Mock 不代表真实接口联调通过。
- 工作台无可信接口的数据保持 `--`，不填充虚构统计值。
- 未创建供应商业务表单；Supplier Master 属于后续业务模块范围。
- 前端权限只控制路由和显示，后端 `require_permission` 仍是安全边界。

## Verification

- 本机 MySQL 已升级至 Revision `20260903_0002`；真实 HTTP 已验证 login、me、
  stateless logout、错误密码、过期 Token、DISABLED 与 deleted 用户。
- 权限拒绝与权限撤销通过 MySQL 集成测试验证；前端权限路由守卫测试已通过。
- 临时联调用户在验证结束后删除；未新增默认账号或硬编码密码。

## Pending

- Refresh Token、Session、Multi-device Logout 属于未来范围，不阻塞当前 Supplier / Product 开发。

## Next Step

Auth Sprint 1 scope completed；无当前 Auth 开发任务。后续业务模块继续使用 `CurrentUser` 与 `require_permission`，不在本模块扩展功能。
