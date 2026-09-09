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
    +-- supplier_quote
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

## 3. 商品与供应商价格

```text
scm_product
    |
    | source_supplier_id：商品大表来源供应商
    v
scm_supplier

scm_product
    |
    | product_id：报价关联
    v
scm_supplier_product_quote
    |
    v
scm_supplier
```

报价记录允许暂未绑定 product_id，后续匹配正式商品。

`source_supplier_id` 仅表示导入来源，不能推导供应商产品报价；Import 不自动创建 Quote。

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
