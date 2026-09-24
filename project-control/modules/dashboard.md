# 工作台统计 / Dashboard

状态：IMPLEMENTED / LIVE_SUMMARY
Owner：feat/dashboard-live-statistics
Last Updated：2026-09-24

## Delivered

- `GET /api/v1/dashboard/summary` 面向所有已登录用户提供运营首页汇总数据。
- 正式商品数与当前 Product 正常列表口径一致：`ACTIVE` Product，且来源 Supplier 未逻辑删除、合作状态为 `NORMAL`。
- 正常合作供应商数为未逻辑删除、已归档且合作状态为 `NORMAL` 的 Supplier。
- 进行中项目包括 `IMPORTED / MATCHING / SELECTING / READY / EXPORTED / SUBMITTED`。
- 待处理事项卡片暂不读取数据，固定显示 `--`；待业务处理入口和状态流转完整跑通后再定义统计口径。
- 对具有 `bid:list` 权限的用户，最近项目按 `updated_at` 倒序返回 5 条，工作台可直接继续进入项目详情或自由推品 Agent；其他用户不返回项目明细。
- 原“建设进度”和“开发边界”已替换为最近项目与权限化快捷入口；开发模式、Sprint 和技术边界不再展示给运营用户。
- 商品、供应商导入快捷入口通过 `?action=import` 进入对应主数据页并直接打开文件选择器；“新建项目”通过 `?action=create` 打开既有创建弹窗。动作触发后立即清理地址栏参数。
- Dashboard API 返回待归档供应商数量，并在“供应商管理”菜单显示角标；商品导入和投标项目目前没有完整的统一待办处理入口，因此不读取待办数量、不显示角标。工作台菜单也不显示角标。
- 全局布局与工作台页面共享 Dashboard Store，避免重复并发请求。
- 收起侧栏时，品牌标志、菜单图标和版本号均以 72px 侧栏为基准水平居中，系统管理分组标题隐藏。

## Boundaries

- 无新表、无 Alembic Revision、无新权限。
- 统计不返回商品或供应商明细；最近项目仅返回编号、名称、类型、状态和更新时间。
