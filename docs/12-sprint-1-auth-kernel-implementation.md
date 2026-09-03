# Sprint 1 Auth Kernel

实现范围：sys_user、sys_role、sys_permission、sys_user_role、sys_role_permission；UUID 使用 ADR-0006 CHAR(36)。密码为 Argon2id，JWT 为 HS256，payload 仅含 sub/ver/iat/exp。API：POST /api/v1/auth/login、GET /api/v1/auth/me、POST /api/v1/auth/logout。无 token/无效 token 返回 401，缺权限返回 403。CurrentUser 从当前数据库加载 roles/permissions；require_permission 为唯一后端授权依赖。

AUTH_JWT_SECRET 必填且不得提交真实值；AUTH_ACCESS_TOKEN_MINUTES 默认 30。Logout 是无状态：服务端仅验证 token 后返回成功，客户端删除 access token；本任务不撤销已复制 token。PENDING：Refresh Token、server-side session、multi-device logout。CI 使用临时 MySQL 与临时 AUTH_JWT_SECRET。
