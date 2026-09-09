# 众诚智链商品管理平台实施计划 V1.3.2

## 1. 一期范围

建设：

1. Auth / RBAC；
2. 供应商主数据；
3. 商品当前成本价与定价；
4. 正式商品主数据；
5. 公司标准商品大表导入；
6. 客户需求；
7. 智能商品匹配；
8. 客户报价；
9. 场景方案；
10. PPTX / PDF；
11. 日志、文件、配置、任务、数据追溯。

一期不做：

- 采购订单；
- 库存；
- 到货验收；
- 退货；
- 物流追踪；
- WMS/ERP完整能力。

## 2. 三套底层正式数据

### 2.1 供应商主数据

回答：

> 谁是供应商？

### 2.2 商品主数据

来源：

> 公司已经整理完成的商品大表。

一期：

> **大表一行 = 一条具体正式商品。**

后续商品查询全部查 MySQL `scm_product`。

### 2.3 商品当前成本价

`scm_product.cost_price` 是具体正式商品的当前成本价，也是当前供应商报价；不建设独立供应商产品报价库。

## 3. 技术栈

- Vue 3 + TypeScript + Vite + Element Plus
- FastAPI / Python 3.12
- SQLAlchemy 2 Async
- Pydantic v2
- Alembic
- MySQL 8
- Redis / ARQ（正式任务）
- MinIO（正式文件）
- InlineTaskQueue / LocalFileStorage（本地开发）
- pytest / Ruff / typecheck

架构：

> Modular Monolith / 模块化单体

## 4. 43个工作日

| Sprint | 时间 | 工期 | 交付 |
|---|---:|---:|---|
| Sprint 0 | D1-D3 | 3 | Local-First 企业底座 |
| Sprint 1 | D4-D8 | 5 | Auth/RBAC + 供应商 |
| Sprint 2 | D9-D13 | 5 | 商品当前成本价与定价 |
| Sprint 3 | D14-D18 | 5 | 商品主数据 / Catalog |
| Sprint 4 | D19-D23 | 5 | 标准商品大表导入 |
| Sprint 5 | D24-D30 | 7 | 客户需求 + 智能报价 |
| Sprint 6 | D31-D36 | 6 | 场景方案 + PPTX/PDF |
| Sprint 7 | D37-D43 | 7 | 测试、部署、验收 |

## 5. Sprint 0 特别说明

Sprint 0 只建设工程底座。

不得提前：

- 创建 Catalog 最终业务表；
- 创建全部业务 Schema；
- 强行设计 SPU/SKU；
- 进入供应商/报价/商品具体业务开发。

商品最终数据库字段必须等真实大表数据字典冻结后再创建正式 Migration。

## 6. 多人协作

Sprint 0 合并 main 后，可以并行：

- Auth / System
- Supplier
- Product Cost Pricing
- Catalog Contract / Data Dictionary
- Frontend Shell

有依赖模块先冻结 Contract，再并行实现。

## 7. Definition of Done

每个任务同时交付：

- Code
- Database/Migration
- Test
- Documentation
- Project Status

缺一不可。
