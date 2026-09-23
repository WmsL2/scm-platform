# Change Record: Product Import Stale Cleanup Transaction Commit

Date: 2026-09-23
Branch: `codex/fix/product-import-stale-cleanup-transaction`
Alembic Revision: 无

## Problem

独立清理命令先用同一 AsyncSession 查询候选 Task ID，触发隐式只读事务。后续清理复用该 Session 时，`transaction_scope` 参与既有事务而未实际提交；命令退出关闭 Session 后删除 SQL 被回滚，但报告错误地统计为已删除。

## Implementation

- 候选 Task ID 查询改为显式独立只读事务；查询结束后事务关闭。
- 每个 Task 后续保持既有短写事务、`FOR UPDATE SKIP LOCKED`、每轮最多 100 条及精确临时媒体处理。
- 不改动 `scm_product` 或正式商品图片。

## Verification

- 新增 MySQL 回归测试：通过 `run()` 清理超过五小时的 `PARTIALLY_CONFIRMED` Task 后，断言报告计数、Task、暂存行、供应商匹配均已在新 Session 中消失；断言仅删除源 Excel 和未导入临时图片 Key。
