# AGENTS.md — 众诚智链商品管理平台强制开发规则

本文件适用于所有开发人员、Codex、Agent。

除非通过正式 ADR 修改，否则不得绕过。

---

# 1. 开始任务前

必须按顺序阅读：

1. `AGENTS.md`
2. `README.md`
3. `project-control/START_HERE.md`
4. `project-control/CURRENT_STATUS.md`
5. 当前 Sprint
6. 当前模块状态
7. 最近相关 Change / Handoff
8. 相关 ADR
9. 当前任务 Prompt

禁止在不了解项目状态的情况下直接改代码。

---

# 2. 技术栈

后端唯一业务后端：

- Python 3.12
- FastAPI
- SQLAlchemy 2.x Async
- Pydantic v2
- Alembic
- MySQL 8

禁止：

- 引入 Spring Boot 作为第二业务后端；
- 一期新增独立 AI 微服务；
- 使用 SQLite 作为正式 Schema 基线。

前端：

- Vue 3
- TypeScript
- Vite
- Element Plus
- Pinia
- Vue Router

---

# 3. Local-First

Docker 不是开发前置条件，也不是 Sprint 0 验收条件。

项目必须支持 Windows / macOS / Linux 本机原生开发。

最低：

- Python 3.12
- Node.js 20+
- MySQL 8

开发默认：

- `TASK_MODE=inline`
- `STORAGE_MODE=local`

正式可切换：

- ARQ + Redis
- MinIO

业务模块禁止直接依赖 Redis / MinIO SDK，必须依赖项目抽象。

---

# 4. FastAPI 分层

标准依赖方向：

`Router -> Permission Dependency -> Application Service -> Domain Rule -> Repository -> SQLAlchemy -> MySQL`

强制：

- Router 不写核心业务逻辑；
- Repository 不决定业务状态；
- ORM Model 与 Pydantic Schema 分离；
- Service 管 Use Case 与事务；
- 金额统一 Decimal；
- 关键写操作必须审计；
- 长任务走 TaskQueue abstraction；
- AI 不得直接写正式业务库。

---

# 5. 商品主数据规则【最高优先级】

公司提供的“商品大表”已经是整理完成的具体正式商品信息。

一期定义：

> **大表一行 = `scm_product` 一条具体正式商品。**

明确：

- 大表不是供应商原始报价表；
- 大表不是 AI 待解析的杂乱商品数据；
- 大表不是只用于生成另一套商品数据的临时来源；
- `scm_import_*` 只负责导入过程；
- 后续正式商品查询只查询 `scm_product` 及受控参数表；
- 商品导入不选择供应商；
- 商品导入不自动创建供应商产品报价；
- 一期不强制 SPU/SKU 二层模型；
- 禁止擅自新增 `scm_product_sku` 并把它作为必需架构；
- 商品最终字段以实际《大表模版.xlsx》为准；
- 在读取大表实际字段前，禁止自行假设商品唯一业务键。

禁止自行规定：

- 型号全局唯一；
- 品牌 + 型号一定唯一；
- 商品名称唯一；
- Excel 行号是业务唯一键。

---

# 6. 供应商规则

- `supplier_code` 只由后端自动生成；
- 全局 UNIQUE；
- 前端不可填写和修改；
- 编码永久不回收；
- 关联只使用 `supplier_id`；
- 禁止供应商名称作为业务外键。

状态：

- `archive_status`: DRAFT / PENDING / ARCHIVED
- `cooperation_status`: NORMAL / STOPPED / BLACKLIST

供应商产品报价只能关联已归档且正常合作供应商。

---

# 7. 供应商产品报价规则

产品报价库和商品主数据是两个独立数据域。

`scm_product`：
> 这个商品是什么？

`scm_supplier_product_quote`：
> 哪个供应商以什么价格供应这个商品？

规则：

- 产品型号是大小写敏感的核心检索字段；
- 型号不是全局 UNIQUE；
- 同型号允许多供应商；
- 同供应商同型号允许多条历史报价；
- 正式历史价格禁止 UPDATE 覆盖；
- 更正采用旧记录 VOID + INSERT 新记录；
- 过期或 VOID 报价不能进入有效报价候选；
- 报价可通过 `product_id` 关联正式商品，未匹配时允许待关联。

---

# 8. 商品导入规则

正确流程：

`标准商品大表 -> 模板校验 -> 字段校验 -> 字典校验 -> 重复/冲突校验 -> 错误预览 -> 人工确认 -> scm_product`

禁止：

- AI 猜表头；
- AI 字段映射；
- 导入时选择供应商；
- 自动生成供应商报价；
- 错误行静默入库。

---

# 9. AI 边界

AI 负责：

- 客户非结构化需求理解；
- 品牌/型号/参数归一化建议；
- 精确规则无法覆盖时的语义候选；
- 场景预算商品组合建议；
- 方案文案。

确定性业务规则负责：

- 正式商品查询；
- 型号/品牌/参数精确匹配；
- 供应商状态过滤；
- 报价有效期；
- 价格计算与排序；
- 权限；
- 审计；
- 数据落库。

AI 输出必须经过 Pydantic Schema 验证。

---

# 10. Alembic 多人协作

- Alembic 是唯一正式 Schema Migration 机制；
- 已进入 main 的 Revision 禁止修改；
- 每次 Schema 变化新增 Revision；
- 多分支 multiple heads 由集成人员 `alembic merge`；
- Change Record 必须记录 Revision ID；
- Schema 变化必须同步数据字典。

---

# 11. Git 多人协作

`main` 禁止直接业务开发。

建议：

- `feat/supplier`
- `feat/supplier-quote`
- `feat/catalog`
- `feat/product-import`
- `fix/...`
- `docs/...`

Commit：

- `feat(supplier): 实现供应商自动编码`
- `fix(supplier-quote): 修复过期报价参与比价`
- `docs(project-control): 更新项目状态`

推荐使用 Git Worktree 让多个开发人员/Codex并行。

---

# 12. 文档同步强制规则

任何功能、模块或阶段性工作准备 Push / PR / Merge 前，必须检查：

## Module Status
更新：

`project-control/modules/{module}.md`

## Change Record
新增：

`project-control/changes/YYYY-MM/YYYY-MM-DD-NNN-description.md`

## CURRENT_STATUS
如果影响总体状态、Sprint、Blocker、Active Branch 或下一任务，必须更新。

## Handoff
未完成或换人接手必须写。

## ADR
重要架构/模型/规则变化必须写。

## 正式 Docs
API、页面、数据库、架构变化必须同步对应文档。

> 文档未更新，任务不得标记 COMPLETED。

---

# 13. 每次任务结束报告

Codex / Agent 最终必须明确报告：

1. 本次完成内容
2. 新增/修改代码文件
3. 新增/修改文档文件
4. Alembic Revision（无则写“无”）
5. API / UI / Permission 变化
6. 测试命令和结果
7. 本机启动验证
8. 未完成事项
9. 下一步建议

没有文档同步不得回复“任务已完成”。
