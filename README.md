# 众诚智链商品管理平台 / Zhongcheng SCM Platform

Repository：`zhongcheng-scm-platform`

版本：**V1.3.2 Fresh Starter**
状态：**SPRINT_0_COMPLETED**

## 1. 项目定位

一期建设：

**供应商主数据 + 正式商品主数据（当前成本价） -> 智能报价 -> 场景方案输出**

一期不建设采购订单、库存、到货验收、退货、物流追踪等 ERP/WMS 模块。

## 2. 已冻结技术栈

### Frontend
- Vue 3
- TypeScript
- Vite
- Element Plus
- Pinia
- Vue Router

### Backend
- Python 3.12
- FastAPI
- SQLAlchemy 2.x Async
- Pydantic v2
- Alembic
- asyncmy

### Database / Infrastructure
- MySQL 8
- Redis：正式缓存/队列依赖，可选本机开发依赖
- ARQ：正式异步任务实现
- MinIO：正式对象存储，可选本机开发依赖
- LocalFileStorage：默认本机开发
- InlineTaskQueue：默认本机开发

### Quality
- pytest / pytest-asyncio
- Ruff
- mypy 或 pyright
- Frontend typecheck/build

## 3. Local-First

开发阶段不要求 Docker。

最低本机环境：

- Git
- Python 3.12
- Node.js 20+
- MySQL 8

默认开发配置：

```env
TASK_MODE=inline
STORAGE_MODE=local
```

Redis / ARQ / MinIO 在需要开发相关功能时再启用。

## 4. 商品主数据最重要定义

公司提供的“商品大表”已经是整理完成的具体商品信息。

一期正式定义：

> **商品大表一行 = 一条具体正式商品。**

导入确认后进入正式 `scm_product`。

后续：

- 商品查询
- 商品筛选
- AI商品匹配
- 客户报价选品
- 场景方案选品
- 商品统计

全部查询正式商品主数据，不长期读取 Excel，也不查询导入暂存表。

一期不强制 SPU/SKU 二层模型。

## 5. 多人 / Multi-Agent

所有开发人员和 Codex 使用同一个 Git Repository 和同一底座。

必须使用：

- Feature Branch
- Pull Request
- 可选 Git Worktree
- Alembic 独立 Revision
- `project-control/` 项目执行记录

## 6. 强制 Definition of Done

> **代码 + 数据库 + 测试 + 文档 + 项目状态 = 一个完整交付。**

代码完成但文档未同步，不视为完成。

## 7. 后续开发

新 Codex 首先读取：

`prompts/00-create-project-foundation.md`

Sprint 0 已稳定完成。开始新任务前请先阅读 `AGENTS.md`、
`project-control/START_HERE.md` 与当前 Sprint 文档；不要重复执行 Sprint 0。

## 8. 本机启动（无需 Docker）

前置条件：Python 3.12、Node.js 20+、MySQL 8，并创建本机数据库
`zhongcheng_scm_dev`。不要使用生产数据库。

```powershell
.\scripts\setup.ps1
.\scripts\start-backend.ps1
# 另一个终端
.\scripts\start-frontend.ps1
```

后端健康检查：`http://localhost:8000/health/live`；就绪检查会验证 MySQL：
`http://localhost:8000/health/ready`。默认 `TASK_MODE=inline`、
`STORAGE_MODE=local`，不要求 Redis、MinIO 或 Docker。
