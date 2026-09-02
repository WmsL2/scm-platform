# Codex Task 00：从零创建众诚智链商品管理平台企业底座

你现在位于一个新的项目目录。

项目：

**众诚智链商品管理平台 / Zhongcheng SCM Platform**

Repository：

`zhongcheng-scm-platform`

你的任务是执行：

**Sprint 0 — Local-First 企业级项目底座**

这是第一次正式代码开发。

---

# 0. 开始前必须阅读

在写任何代码前完整阅读：

1. `AGENTS.md`
2. `README.md`
3. `docs/00-project-plan.md`
4. `docs/01-architecture.md`
5. `docs/02-pages.md`
6. `docs/03-codex-plan.md`
7. `docs/04-project-tree.md`
8. `docs/05-fastapi-conventions.md`
9. `docs/06-local-development.md`
10. `docs/07-product-master-data.md`
11. `docs/08-database-roadmap.md`
12. `project-control/START_HERE.md`
13. `project-control/CURRENT_STATUS.md`
14. `project-control/sprints/sprint-00-foundation.md`
15. `project-control/decisions/` 下全部 ADR

阅读后检查当前 Git 状态和仓库目录。

---

# 1. Sprint 0 范围

只建设企业工程底座。

不要开发：

- 供应商具体业务；
- 产品报价业务；
- 商品业务；
- 商品大表实际导入业务；
- 智能报价；
- 场景方案。

不要一次创建全部业务表。

不要因为通用电商习惯创建 SPU/SKU 业务结构。

---

# 2. 技术栈

## Frontend
- Vue 3
- TypeScript strict
- Vite
- Element Plus
- Pinia
- Vue Router

## Backend
- Python 3.12
- FastAPI
- SQLAlchemy 2.x Async
- asyncmy
- Pydantic v2
- pydantic-settings
- Alembic

## DB
- MySQL 8

## Local-First
默认：

`TASK_MODE=inline`
`STORAGE_MODE=local`

Redis / ARQ / MinIO 不得成为本机启动前置条件。

禁止 Docker 作为 Sprint 0 必需项。

---

# 3. 创建 Monorepo

按照 `docs/04-project-tree.md` 创建真实代码目录。

重点：

- `apps/web-admin`
- `apps/api-server`
- `scripts`
- `.github/workflows`

保留已有 docs / project-control / prompts。

---

# 4. Backend 必须完成

创建 FastAPI 最小企业底座：

## Core
- Settings
- Async SQLAlchemy Engine / Session
- lifespan
- CORS
- Request ID middleware
- structured logging
- global exception handler
- OpenAPI metadata

## Common
- unified response
- error response
- pagination
- base ORM mixins
- audit abstraction
- permission dependency placeholder
- business sequence abstraction
- idempotency abstraction

## Infrastructure abstraction

### TaskQueue
- Protocol / interface
- `InlineTaskQueue`
- `ArqTaskQueue` skeleton/adapter boundary

### ObjectStorage
- Protocol / interface
- `LocalFileStorage`
- `MinioStorage` adapter boundary

### Cache
- abstraction
- Redis adapter boundary

业务代码不能直接依赖 Redis / MinIO SDK。

## Health
- `GET /health/live`
- `GET /health/ready`

ready：
- 默认必须检查 MySQL；
- 只有配置启用了 Redis/MinIO时才检查相应依赖。

---

# 5. Alembic

建立正确的 Async Alembic 配置。

要求：

- 可以连接本机 MySQL 8；
- 创建最小 baseline revision；
- `alembic upgrade head` 成功。

不要创建 Supplier / Product / Quote 等业务表。

商品业务 Schema 必须等待真实大表数据字典冻结。

---

# 6. Frontend

创建：

- Vue 3
- TS strict
- Element Plus
- Pinia
- Router
- HTTP client
- Basic Layout
- Placeholder Home
- 404
- env configuration

Sprint 0 不开发业务页面。

---

# 7. Local Development Scripts

必须支持 Windows：

- `scripts/setup.ps1`
- `scripts/start-backend.ps1`
- `scripts/start-frontend.ps1`

支持 macOS/Linux：

- `scripts/setup.sh`
- `scripts/start-backend.sh`
- `scripts/start-frontend.sh`

不得依赖 Docker。

---

# 8. Quality

Backend：

- pytest
- pytest-asyncio
- Ruff
- mypy 或 pyright

Frontend：

- typecheck
- build

至少测试：

- `/health/live`
- `/health/ready` 关键行为
- `InlineTaskQueue`
- `LocalFileStorage`
- unified response/error 基础能力

---

# 9. CI

创建基础 CI：

Backend：
- install
- Ruff
- typecheck
- pytest

Frontend：
- install
- typecheck
- build

CI可以按平台能力使用MySQL service，但开发人员本机不要求Docker。

---

# 10. 商品规则必须保留

即使 Sprint 0 不开发商品业务，也必须保证新工程文档中没有与以下规则冲突的设计：

- 商品大表是正式商品主数据；
- 大表一行 = 一条具体商品；
- 正式查询基于 `scm_product`；
- Import表只做 Staging；
- 一期不强制 SPU/SKU；
- 商品最终字段和唯一键等待真实大表数据字典。

全仓库检查：

`SPU`
`SKU`
`scm_product_sku`
`商品大表`
`scm_product`

如生成的新代码/文档出现与当前 ADR 冲突内容，立即修正。

---

# 11. 文档同步

完成代码后强制：

1. 更新 `project-control/CURRENT_STATUS.md`
2. 更新 `project-control/sprints/sprint-00-foundation.md`
3. 更新 `project-control/modules/system.md`
4. 新增一份 Change Record
5. 未完成工作写 Handoff
6. 新的架构决定写 ADR
7. 更新 README 本机启动命令
8. 更新 Local Development 文档（如启动方式变化）

文档未同步不得标记 Sprint 0 完成。

---

# 12. 实际验收

必须实际运行并记录：

## Backend
- Python venv
- dependencies install
- FastAPI local start
- `/health/live` -> 200
- `/health/ready` -> 200（MySQL正常）
- `alembic upgrade head`
- pytest PASS
- Ruff PASS
- typecheck PASS

## Frontend
- dependency install
- dev server start
- typecheck PASS
- build PASS

## Local adapters
- InlineTaskQueue test PASS
- LocalFileStorage test PASS

Docker 不属于验收项。

---

# 13. 工作方式

按小步骤实施，不要无检查地一次生成整个工程。

推荐：

1. Root / configs
2. Backend skeleton
3. DB / Alembic
4. Local adapters
5. Health / errors / logging
6. Frontend skeleton
7. Scripts
8. Tests
9. CI
10. Docs sync
11. Final validation

每完成一部分先运行对应检查再继续。

---

# 14. 最终报告

最终必须输出：

## 已完成
## 新增/修改代码文件
## 新增/修改文档文件
## Alembic Revision
## 本机启动验证
## Test / Ruff / Typecheck / Build
## 商品主数据规则检查结果
## 未完成事项
## 下一步建议

没有未完成事项时明确：

`未完成事项：无`
