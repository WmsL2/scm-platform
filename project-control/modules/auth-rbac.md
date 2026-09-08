# Auth/RBAC

状态：AUTH SPRINT 1 SCOPE IMPLEMENTED / VERIFIED

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
- Web Admin UI Optimization（`feat/web-admin-ui-optimization`）：用户管理以中文标签显示用户
  状态、以角色名称显示所属角色，不显示角色 UUID；用户响应新增兼容的只读 `role_names`。角色权限
  不显示权限 UUID；待审批注册数使用真实 API `total` 显示在“注册审批”菜单红色角标中，审批后
  即时刷新。只有 `ENABLED` 用户可分配角色，前端隐藏其他状态的操作，后端返回
  `ACCOUNT_USER_NOT_ENABLED` 拒绝绕过页面的写入。前后端测试、typecheck 和 production build
  已通过；浏览器验收待完成。
- 注册审批页面提供待审批与审批历史两个页签。审批历史使用同一查看审批权限，按
  `reviewed_at` 倒序、分页展示已处理申请的审批结果、时间与说明；待审批申请不会进入历史。
- 自定义角色可由 `system:role:create` 创建：角色编码采用不可修改的小写英文、数字和下划线，
  角色名称为展示文本，初始权限为空；创建者与更新者记录为当前操作用户。创建成功后，如同时具备
  权限目录与角色权限更新权限，前端直接进入“配置权限”。本期不提供角色编辑、停用或删除。
- 角色权限保存为单次提交：保存期间前端禁止重复提交。若当前操作人编辑自己所属角色，后端必须保留
  `system:role:list`、`system:permission:list` 与 `system:role:permission:update` 的有效组合，防止
  操作人将自己锁出角色管理。

## Account / Registration / Profile

- 注册：`POST /api/v1/auth/register` 创建 `PENDING` 用户；状态机包含
  `PENDING`、`ENABLED`、`DISABLED` 与 `REJECTED`。`PENDING` 和 `REJECTED`
  用户不能登录。
- 审批：注册申请可由具有对应 `system:registration:*` 权限的管理员审批或拒绝，
  并记录 `reviewed_by`、`reviewed_at`、`review_note`。
- 管理：管理员 API 支持用户列表、整体替换用户角色、角色列表、整体替换角色权限、
  动态权限目录以及注册申请列表/审批；全部管理员入口继续使用
  `require_permission`。
- 权限：目录包括 `system:user:list`、`system:user:role:update`、
  `system:role:list`、`system:role:create`、`system:role:permission:update`、
  `system:permission:list`、`system:registration:list`、
  `system:registration:review` 八项权限，并动态从 `sys_permission` 读取。
- 个人信息：前端提供 `/register`、`/admin/users`、`/admin/roles`、
  `/admin/registrations`、完整 Profile Dropdown 与 Change Password Dialog。系统管理菜单、
  角色分配、权限分配和审批操作均按各自权限单独控制，不使用硬编码管理员用户名或角色。
- 修改密码：`POST /api/v1/auth/change-password` 校验当前密码，使用现有 Argon2id
  哈希策略保存新密码，并在成功事务中令 `token_version + 1`，使旧 Token 失效。
- Migration：Revision `20260908_0007`，down revision `20260908_0006`。新增
  `system:role:create` 权限；如存在未删除的 `system_administrator` 内置角色，迁移会为其赋予该权限。
  Supplier
  Delete & Import 先合入后，原临时 Account `0005` 调整为 `0006`；未创建 merge migration。

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
- Account / Registration / Profile：Backend Ruff、mypy 通过，pytest 51 passed；
  Frontend Vitest 22 passed，typecheck 与 build 通过；Alembic heads/current 为
  `20260908_0006`，Supplier schema integration test 通过。

## Post-Merge Hardening

- Request-scoped Session 现在拥有 HTTP 事务；AccountService 在调用方已有事务时仅参与，
  不再自行 commit 或 rollback。
- 用户角色和角色权限整体替换会按输入顺序去重后再校验、写入和返回；重复 UUID
  不会导致关联表联合主键冲突。
- 注册用户名并发唯一冲突在 SAVEPOINT 中恢复并映射为
  `ACCOUNT_USERNAME_EXISTS`，外层事务仍由调用方决定。
- ADR-0007 冻结事务所有权规则；本次无 Migration，Alembic 继续为单 Head
  `20260908_0006`。

## Pending

- Refresh Token、Session、Multi-device Logout 属于未来范围，不阻塞当前 Supplier / Product 开发。
- Role Delete / disable policy 尚未冻结；REJECTED username reapply / reopen policy 尚未实现。

## Next Step

Auth Sprint 1 当前范围已实现并验证；未来 Auth 范围仍以 Pending 为准。后续业务模块继续使用 `CurrentUser` 与 `require_permission`，下一业务重点为 Product / Category / Pricing。
