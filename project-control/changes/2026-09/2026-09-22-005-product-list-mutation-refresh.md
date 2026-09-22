# 2026-09-22-005：商品列表 Mutation 后即时刷新

- 商品 Excel 确认导入、新增/更新结果、停用、启用和永久删除成功后，统一重新请求 Product List；不使用页面重载、路由重载或 WebSocket。
- 导入确认固定刷新第一页；停用、启用和永久删除若移除当前页唯一一条记录，会自动刷新上一页。
- 所有上述刷新会清空跨页商品选择集合，避免已停用或删除的 ID 被继续用于导出。
- Product List GET 引入递增请求序列，仅最新请求可写入列表、总数、页码与 loading，旧慢响应不会覆盖 mutation 刷新结果。
- ProductDetailView 维持 API 返回值直接写入本地 Product 的即时更新逻辑，不作修改。
- Alembic Revision：无；API、权限、后端生产代码：无变化。
