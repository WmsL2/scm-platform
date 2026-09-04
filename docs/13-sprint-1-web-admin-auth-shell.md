# Sprint 1 Web Admin Auth Shell

状态：IMPLEMENTED；实现分支为 `feat/web-admin-auth-shell`，真实 Auth API 验收待完成。

## Scope

本任务只建设 Web Admin 的认证入口与通用后台壳层，不实现 Supplier、Product、Quote 等业务页面。

## Routes

| Route | Purpose | Auth |
|---|---|---|
| `/login` | 用户名密码登录 | Public |
| `/dashboard` | 企业工作台 | Required |
| `/403` | 无权限提示 | Required |
| `/:pathMatch(.*)*` | 404 | Public |

受保护路由使用 `meta.requiresAuth`；未来业务路由可使用 `meta.permission`。前端权限仅改善交互，后端 `require_permission` 是唯一安全边界。

## Auth Flow

```text
LoginView
  -> Auth Store
  -> authApi.login
  -> token localStorage
  -> authApi.me
  -> CurrentUser roles / permissions
  -> Router Guard
```

页面刷新时 Auth Store 使用已保存 Token 调用 `/api/v1/auth/me`。401 清除本地状态并跳转登录页；403 跳转 `/403`。前端不解析 JWT 中的角色或权限。

## Environment

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK=false
VITE_APP_TITLE=众诚智链商品管理平台
```

- `.env.example` 默认关闭 Mock；需要纯前端演示时，在本机未提交的 `.env` 中设置 `VITE_USE_MOCK=true`；
- `VITE_USE_MOCK=true`：仅在 `npm run dev` 的 Vite 开发模式下使用本机演示账号 `admin / admin123`，不访问后端数据库；
- `VITE_USE_MOCK=false`：调用 FastAPI 的 login、me、logout；
- 生产构建无论环境变量如何都强制关闭 Mock，调用真实 API；
- 页面会明确显示 Mock 或真实 API 模式，禁止把 Mock 验收描述为真实接口验收。

## Data Boundary

工作台的商品、供应商、报价和导入统计尚无正式 API。对应值统一显示 `--`，并标注等待接口，不使用前端硬编码业务数字。

Supplier Field Gate 未解除前，不创建供应商新增/编辑表单，不假设企业名称、税号、银行、联系人等字段。

## Verification

```powershell
cd apps/web-admin
npm run test
npm run typecheck
npm run build
npm run dev
```

真实接口验收必须在 Auth Migration 完整的 MySQL 8 开发库上单独执行。
