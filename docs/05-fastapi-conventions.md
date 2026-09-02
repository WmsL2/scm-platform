# FastAPI 企业开发规范 V1.3.2

## 1. 模块结构

```text
modules/{module}/
├─ api/
├─ application/
├─ domain/
├─ infrastructure/
├─ schemas/
└─ dependencies.py
```

## 2. 依赖方向

`API -> Application -> Domain -> Infrastructure`

禁止反向依赖。

## 3. Router

只负责：

- HTTP
- Schema
- Dependency
- 调 Service
- Response

不得写复杂 SQL 或业务状态机。

## 4. Application Service

负责：

- Use Case
- Transaction
- 调多个 Repository
- Audit
- Task enqueue

## 5. Domain

负责不可变业务规则和状态判断。

## 6. Repository

负责持久化，不决定业务规则。

## 7. ORM / Schema

SQLAlchemy ORM 与 Pydantic Schema 分开。

## 8. Database

- AsyncSession
- Money = Decimal
- UTC/统一时区策略需冻结
- 重要唯一性必须数据库 Constraint
- Alembic 管 Schema

## 9. Infrastructure Abstraction

业务只依赖：

- TaskQueue
- ObjectStorage
- Cache
- AIProvider

## 10. Error

统一业务错误码和全局异常处理。

## 11. Logging

至少：

- request_id
- user_id（登录后）
- method
- path
- elapsed
- result

禁止记录密码、Token、API Key。

## 12. Tests

- Domain Rule：Unit
- Repository：Integration
- API：API Test
- 核心状态机和金额计算必须测试。
