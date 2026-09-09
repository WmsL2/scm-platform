# 系统架构 V1.3.2

## 1. 总体结构

```text
Vue 3 Admin
    |
    v
FastAPI Modular Monolith
    |
    +-- auth / system
    +-- supplier
    +-- catalog
    +-- product_import
    +-- requirement
    +-- matching
    +-- quotation
    +-- solution
    +-- ai
    |
    +-- MySQL 8
    |
    +-- TaskQueue
    |    +-- InlineTaskQueue (dev)
    |    +-- ArqTaskQueue (prod)
    |
    +-- ObjectStorage
    |    +-- LocalFileStorage (dev)
    |    +-- MinioStorage (prod)
    |
    +-- Cache
         +-- Dev/Noop adapter
         +-- RedisCache
```

## 2. 商品数据

```text
公司商品大表
     |
     v
Import Staging（supplier_name_raw）
     |
     v
Supplier Matching（按批次+标准化名称）
     |
     v
Confirm 原子校验 → scm_product（source_supplier_id）正式商品主数据
     |
     +--> 商品查询
     +--> AI匹配
     +--> 客户报价
     +--> 场景方案
```

Import Staging 不能作为长期商品查询库。

## 3. 商品与当前成本价

```text
scm_product
    |
    | source_supplier_id：商品大表来源供应商（非当前报价供应商）
    v
scm_supplier

scm_product.cost_price
    |
    +--> 当前成本价（业务确认的当前供应商报价）
    +--> Pricing Service 重算派生价格与毛利
```

一期不创建 `scm_supplier_product_quote`，也不建设报价历史、有效期、作废或多供应商比价。供应商新报价由后续 Product Backend 直接更新目标 Product 的 `cost_price`；更新必须原子重算并保存派生价格，使用 Product 的既有审计字段记录操作者和时间。

## 4. Backend 分层

`Router -> Application Service -> Domain -> Repository -> SQLAlchemy`

公共设施：

- DB Session
- Audit
- Business Sequence
- TaskQueue
- ObjectStorage
- Cache
- Permission
- AI Provider

## 5. Local-First

Docker 非必需。

最低：

- Python
- Node.js
- MySQL

Redis/MinIO按需启用。

## 6. 模块化单体

一期不拆业务微服务。

未来确有规模、团队和独立部署需求时再拆分。
