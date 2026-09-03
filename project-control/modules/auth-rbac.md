# Auth/RBAC

状态：MERGED / DONE

数据库：五张 Auth/RBAC 表，Revision 20260903_0002。
API：login、me、logout。
权限：CurrentUser、get_current_user、require_permission。
安全：Argon2id、HS256、token_version。
Merge：PR #6 已合入 `main`（Merge Commit `6f229e75`）；实现提交 `d90d519`，CI 修复提交 `066e4df`。
测试：30 passed（Foundation 13 + Auth 17），Warnings 0；Ruff PASS，mypy PASS。Auth 覆盖密码、JWT API 的 `sub`/`ver`/`iat`/`exp` 必填 claims、login/me/logout、token_version、已签发 Token 对 DISABLED / deleted 用户、权限动态授予/撤销与逻辑删除 Role 即时失效、登录失败矩阵、活跃用户名生成列唯一性，以及真实 MySQL 的 FK、RESTRICT、CHECK、UNIQUE、辅助索引与 UUID CHAR(36) 合同。
Pending：Refresh Token、Session、Multi-device Logout、Business Sequence。
Next Step：Business Sequence；Supplier Gate 保持有效。
