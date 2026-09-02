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

```env
TASK_MODE=inline
STORAGE_MODE=local
```

Redis / MinIO 非 Sprint 0 强制依赖。

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
