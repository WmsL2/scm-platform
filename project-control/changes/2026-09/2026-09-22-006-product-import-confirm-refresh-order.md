# 2026-09-22-006：商品 Confirm 后优先刷新正式列表

- Product Import Confirm 成功后先以第 1 页重新请求正式 Product List，再提示并关闭预览；不再为即将关闭的弹窗回读导入明细。
- 普通关闭按钮保留当前筛选和页码刷新列表后关闭；Confirm 成功（含 `PARTIALLY_CONFIRMED`）清空预览状态再关闭，避免 `@closed` 对已确认任务执行 discard。
- 保留既有筛选、跨页选择清理、请求序列保护、计时和导入导航锁；不修改后端、API、权限或数据库。
