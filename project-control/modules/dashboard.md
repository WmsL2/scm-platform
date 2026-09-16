# 工作台统计 / Dashboard

状态：IMPLEMENTED / LIVE_SUMMARY
Owner：feat/dashboard-live-statistics
Last Updated：2026-09-16

## Delivered

- `GET /api/v1/dashboard/summary` 面向所有已登录用户提供首页汇总数据。
- 正式商品数与当前 Product 正常列表口径一致：`ACTIVE` Product，且来源 Supplier 未逻辑删除、合作状态为 `NORMAL`。
- 已归档供应商数为未逻辑删除且 `archive_status = ARCHIVED` 的 Supplier；停止合作或拉黑不改变其归档事实。
- 首页仅接入“正式商品”和“已归档供应商”两张卡片；其余卡片继续明确显示未建设状态。
- 收起侧栏时，品牌标志、菜单图标和版本号均以 72px 侧栏为基准水平居中，系统管理分组标题隐藏。

## Boundaries

- 无新表、无 Alembic Revision、无新权限。
- 统计仅返回数量，不返回商品或供应商明细。
