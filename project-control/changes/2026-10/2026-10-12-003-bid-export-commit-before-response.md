# Change Record：投标报价导出响应前提交

日期：2026-10-12  
分支：`feat/type2-brand-normalization`  
模块：bid / matching

## 问题

类型 1/2 工作台调用报价导出 POST 后，会立即使用响应中的文件 ID 发起下载 GET。投标导出路由仍使用请求级数据库依赖，响应可能先于依赖事务提交发送；下载请求使用另一数据库会话时暂时看不到新附件记录，返回 404“投标文件不存在”。文件和数据库记录实际已经生成，因此稍后重试通常可以下载。

## 修复

- 投标导出 POST 改用 function-scope 数据库依赖，确保附件、状态和审计事务在响应发送前完成提交。
- 导出权限依赖同步使用响应前完成的认证依赖，与既有推荐导出保持一致。
- 新增路由依赖作用域回归测试，防止投标导出退回请求结束后提交。

## 数据库、API 与权限

- Alembic Revision：无。
- API、UI、权限码及文件格式：无变化。
- 事务规则：遵循 ADR-0007。

## 验证

- `pytest tests/bid/test_bid_routes.py tests/bid/test_bid_project_foundation.py -q`：8 passed。
- `pytest tests/bid tests/matching -q`：38 passed。
- `ruff check app/modules/bid/api/router.py tests/bid/test_bid_routes.py`：通过。
- `mypy app/modules/bid/api/router.py`：通过。
