# ADR-0016：短期访问令牌与服务端刷新会话

状态：ACCEPTED
日期：2026-09-11

## Context

原认证仅使用保存在 `localStorage` 的短期 Access Token，Logout 不撤销服务端状态。用户需要在持续使用系统时保持登录，同时要求三天无活动自动退出，并在退出、修改密码、账号停用或删除后立即失效。

## Decision

- Access Token 继续使用 HS256 JWT，默认有效期 30 分钟；新增 `sid` 绑定服务端会话和 `jti` 唯一标识。前端仅在内存保存 Access Token，不再持久化到 Web Storage。
- Refresh Token 使用高熵随机值，仅通过 `HttpOnly`、`SameSite=Lax`、限定 `/api/v1/auth` 路径的 Cookie 传输；生产环境默认启用 `Secure`。
- Revision `20260911_0021` 新增 `sys_auth_session`，仅保存 Refresh Token SHA-256 哈希、轮换状态、最后活动时间、闲置/绝对到期时间和撤销原因，不保存明文 Refresh Token。
- 会话采用三天滑动闲置过期和三十天绝对过期。成功刷新时更新活动时间、轮换 Refresh Token，并签发新的 Access Token；绝对期限不会因刷新延长。
- Refresh Token 重放会撤销对应会话。为避免同一浏览器多标签页的近并发刷新互相退出，上一枚令牌只在默认 30 秒宽限窗口内可再次轮换。
- 前端遇到受保护请求 401 时只进行一次共享刷新并只重试原请求一次；刷新失败后清除内存状态并返回登录页。
- Logout 同时撤销签名 Bearer Token 和当前 Cookie 对应的会话。修改密码和用户逻辑删除撤销该用户全部会话；账号不是 `ENABLED` 时 Access Token 立即被拒绝，Refresh 会话也会撤销。

## Reason

该方案把长期登录能力放在不可被前端脚本读取的 Cookie 与可撤销的服务端会话中，同时保留短期 JWT 的接口使用方式。滑动过期满足持续工作的体验，绝对过期、令牌轮换和服务端撤销限制凭证泄露后的风险。

## Consequences

- 后端每次验证带 `sid` 的 Access Token 都会检查对应会话，因此 Logout 可以立即使已签发 Access Token 失效。
- `sys_auth_session.user_id` 使用 `ON DELETE CASCADE`，因为会话是可撤销的安全状态而不是业务审计记录；应用内用户仍只允许逻辑删除。
- 本地 HTTP 开发环境自动关闭 Cookie `Secure`；生产部署应使用 HTTPS，并可显式配置所有会话时限。
- 历史上不含 `sid` 的 JWT 仅作为迁移兼容路径；登录和刷新接口签发的新 Token 均绑定会话。

## Related

- ADR-0006 MySQL UUID CHAR(36)
- ADR-0007 Request Transaction Ownership
