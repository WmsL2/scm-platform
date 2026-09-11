# Sprint 1 Auth Kernel

实现范围：sys_user、sys_role、sys_permission、sys_user_role、sys_role_permission、sys_auth_session；UUID 使用 ADR-0006 CHAR(36)。密码为 Argon2id，Access Token 为 HS256 JWT，payload 含 sub/ver/sid/jti/iat/exp，不保存角色和权限快照。API：POST /api/v1/auth/login、POST /api/v1/auth/refresh、GET /api/v1/auth/me、POST /api/v1/auth/logout。无 token/无效 token 返回 401，缺权限返回 403。CurrentUser 从当前数据库加载 roles/permissions；require_permission 为唯一后端授权依赖。

AUTH_JWT_SECRET 必填且不得提交真实值；Access Token 默认 30 分钟。Revision `20260911_0021` 按 ADR-0016 实现服务端会话：Refresh Token 仅在 HttpOnly Cookie 中传输且数据库只保存哈希；三天无刷新活动自动过期，三十天绝对过期；成功刷新执行令牌轮换。Logout 撤销当前会话，改密和用户删除撤销全部设备会话，DISABLED/deleted 用户立即失效。前端 Access Token 仅驻留内存，401 自动刷新并重试一次。CI 使用临时 MySQL 与临时 AUTH_JWT_SECRET。
