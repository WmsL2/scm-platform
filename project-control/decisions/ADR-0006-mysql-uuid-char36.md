# ADR-0006: MySQL UUID CHAR(36)

状态：ACCEPTED

Python 使用 uuid.UUID；MySQL 所有 UUID PK/FK 统一 CHAR(36)，通过 UUIDChar36 TypeDecorator 绑定和恢复。禁止混用 VARCHAR、BINARY(16) 或 CHAR(32)。CHAR(36) 便于 Sprint 1 排障和审查；未来改 BINARY(16) 必须有新 ADR 与 Migration。
