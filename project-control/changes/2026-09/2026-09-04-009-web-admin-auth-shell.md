# Change Record: Web Admin Auth Shell

Change ID: 2026-09-04-009
Module: auth-rbac / web-admin
Branch: feat/web-admin-auth-shell

## Changes

- 完成登录页面、Pinia 认证状态、Token 持久化和刷新恢复；
- 封装既有 login、me、logout 契约，扩展统一 HTTP Client；
- 增加登录与权限路由守卫，以及 401/403 全局处理；
- 完成企业后台 Layout、工作区 Tab、工作台、403 和 404；
- 增加显式本地 Mock 模式，Mock 与真实 FastAPI 使用同一 Schema；
- 限制 Mock 只在 Vite 开发模式生效，生产构建强制使用真实 API；
- 工作台未接入的业务数据使用 `--`，不写入虚构统计值；
- 增加 Vitest 和前端认证/HTTP 单元测试；
- 将前端单元测试加入 GitHub Actions，并统一 lockfile 的 npm Registry 来源；
- 升级 Element Plus、Vite、Vitest 及相关传递依赖到安全修复版本，并将 Vite Vue 插件归入开发依赖；
- 新增真实 Auth API 联调 Handoff，明确后端开发库修复后的验收清单；
- 同步 CURRENT_STATUS 的 Sprint 进度、下一步、联调依赖和 Active Branch。

## Boundaries

- 未修改后端、数据库 Schema、Alembic Revision 或权限编码；
- 未创建 Supplier、Product、Quote 页面或字段；
- `VITE_USE_MOCK=true` 仅在 Vite 开发模式下代表前端本地演示，生产构建不会启用 Mock，也不代表真实 API 联调；
- Supplier Field Gate 和 Business Sequence 后端任务不受本变更影响。

## API / UI / Permission

- API：只消费既有 `POST /api/v1/auth/login`、`GET /api/v1/auth/me`、`POST /api/v1/auth/logout`；
- UI：新增 `/login`、`/dashboard`、`/403`，保留统一 404；
- Permission：新增前端 Route Meta 检查能力，后端仍是唯一安全边界。

## Verification

- `npm run test`：10 passed；
- `npm run typecheck`：PASS；
- `npm run build`：PASS；
- 生产产物检查：未包含 Mock 密码、Token 前缀或 Mock 认证错误标记；
- `npm audit --offline`：生产依赖与完整依赖均为 0 vulnerabilities；官方 Registry 在线审计端点复核时出现网络超时；
- 浏览器：Mock 登录、刷新恢复、退出、403、404 均已通过本机验收。

## Database

Alembic Revision：无。

## Next Step

在迁移完整的开发数据库上关闭 Mock，完成真实 login/me/logout 联调；业务页面按模块拆分独立分支。
