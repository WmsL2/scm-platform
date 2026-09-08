# ADR-0007：Request Transaction Ownership

状态：ACCEPTED
日期：2026-09-08

## Context

HTTP 路由、认证依赖和业务 Service 共享同一个 AsyncSession。此前部分 Service 在发现已有事务后仍自行 commit 或 rollback，可能提前结束调用方拥有的事务；局部数据库唯一约束冲突也可能错误地回滚整个调用方事务。

## Decision

- `get_db_session()` 为每个 HTTP Request 开启并拥有一个事务：Endpoint 正常完成时提交，异常时回滚。
- Service 收到已有事务的 Session 时只参与事务，绝不 commit 或 rollback 调用方事务。
- Service 收到无活动事务的全新 Session 时，通过共享 `transaction_scope()` 创建并拥有事务。
- 局部唯一约束冲突恢复使用 nested transaction / SAVEPOINT；不以 `session.rollback()` 处理该局部冲突。

## Reason

统一事务所有权可保证一个 Request 内的多项写入原子完成，也保留非 HTTP 调用方包裹多个 Service 操作并决定提交或回滚的能力。

## Consequences

- 路由可达 Service 不再维护各自不同的 commit / rollback helper。
- 需要将可恢复的局部持久化冲突放入 SAVEPOINT。
- BusinessSequenceService 继续遵守 caller-owned transaction 语义，不改变其业务取号规则。

## Related

- `apps/api-server/app/core/database.py`
- `apps/api-server/app/core/transaction.py`
- Change Record `2026-09-08-019`
