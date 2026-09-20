# 本机开发指南 / Local Development

## 必需

- Git
- Python 3.12
- Node.js 20+
- MySQL 8

## Backend

Windows：

```powershell
cd apps/api-server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

macOS/Linux：

```bash
cd apps/api-server
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

## Frontend

```bash
cd apps/web-admin
npm install
npm run dev
```

## 默认开发

首次部署可在 API 的 `.env` 设置一次性初始化管理员：

```env
INITIAL_ADMIN_USERNAME=platform-admin
INITIAL_ADMIN_PASSWORD=replace-with-a-long-random-password
```

应用在数据库 Migration 完成后启动时会创建已启用的 `boss` 账号，并授予该角色当前全部权限。创建成功后应从部署环境删除这两个变量；即使变量误保留，系统也不会复活或重建后来删除的同名账号。

```env
TASK_MODE=inline
STORAGE_MODE=local
```

Redis / MinIO 非 Sprint 0 强制依赖。

## 局域网开发访问

局域网临时演示可让前端和后端分别监听 `0.0.0.0`，并在前端 `.env` 中把
`VITE_API_BASE_URL` 配置为服务器的局域网 IP（例如 `http://192.168.2.250:8000`）。
后端 `CORS_ORIGINS` 必须包含对应前端地址（例如
`http://192.168.2.250:5173`）。仅在 Windows 防火墙中向实际局域网网段放行
`5173` 和 `8000`，不得开放 MySQL `3306`。正式部署应使用 HTTPS。

普通 HTTP 的局域网 IP 不属于浏览器安全上下文；前端请求 ID 已提供兼容回退，
不会因 `crypto.randomUUID()` 不可用而阻止 API 请求。

## 项目脚本

在项目根目录可以使用跨平台脚本完成相同操作：

```powershell
.\scripts\setup.ps1
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
```

```bash
./scripts/setup.sh
./scripts/start-backend.sh
./scripts/start-frontend.sh
```

就绪检查 `GET /health/ready` 始终验证 MySQL；仅当后续配置显式启用
Redis 或 MinIO 时，才应把这些依赖加入相应的 readiness 检查。

## MySQL

建议每人独立开发数据库：

`zhongcheng_scm_dev`

不得连接生产数据库开发。
