# 2026-09-22-008：供应商 Excel 导出

- 新增 `GET /api/v1/suppliers/selection-ids`，复用 `supplier:list` 与列表筛选语义，返回当前筛选条件下全部未删除 Supplier ID 与 total；无分页参数。
- `POST /api/v1/suppliers/export` 仅接收非空、无重复的 `supplier_ids`，仅导出最终选择的 Supplier。若选中对象缺失或已逻辑删除，返回 `409 SUPPLIER_EXPORT_SELECTION_STALE`，不静默漏导。
- 前端采用商品列表一致的单选/多选/跨页选择模型：表头 checkbox 只影响当前页；“全选全部供应商（N）”选择当前筛选结果全量，查询、重置和删除会清理对应选择。
- Excel 包含冻结供应商字段、有效联系人、中文状态与时间；供应商编码和电话按文本写入。
- 无 Migration、无新 Permission。

## Test Closure

- 后端专项覆盖 selection-ids 的筛选、超分页、逻辑删除、权限、total 一致性，以及 POST 导出的空/重复 ID、失效选择、Excel 内容和联系人合同。
- 前端 `supplier.spec.ts` 断言 selection-ids 只携带非分页筛选参数、导出经 `http.postBlob()` 发送 selected IDs；supplier selection helper 覆盖跨页合并、取消与全选判断，页面复用既有“供应商 Excel 导出”Operation Timer。
- 完整回归：Backend Supplier 44 passed、Backend 全量 216 passed；Frontend Vitest 29 files / 126 tests passed，typecheck 与 production build passed。
- `alembic heads`：`20260922_0038 (head)`；本功能未新增 Migration 或 Permission。
