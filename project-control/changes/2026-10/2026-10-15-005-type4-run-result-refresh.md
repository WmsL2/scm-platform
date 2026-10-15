# 类型 4 推品刷新竞态与确认后提前导出

日期：2026-10-15  
状态：COMPLETED  
分支：`fix/type4-run-result-refresh`

## 背景

类型 4 工作台在网络较慢或轮询相邻周期重叠时，可能先后收到同一 Run 的两个快照。较早请求在候选提交前读取到空候选页，却可能晚于完成后的请求返回，从而覆盖页面中已生成的候选结果。

同时，既有导出要求项目先完成选品，无法在人工确认部分商品后先生成阶段性 Excel。

## 变更

- 工作台每次刷新 Run 时递增刷新代次；仅当前代次、且仍对应当前展示 Run 的响应可以写入页面状态。
- 轮询增加单飞保护：未完成的轮询刷新期间不会启动新的轮询请求。
- 组件卸载时使全部未完成刷新失效，避免离开页面后的迟到响应更新状态。
- `SELECTING` 状态下已确认至少一件商品即可从候选工具栏生成版本化 Excel；生成后继续保留 `SELECTING`/`CONFIRMED`，可继续确认或撤销。
- 完成选品后的导出继续将项目/Run 标记为最终导出状态；导出前的阶段性 Excel 不提前改变该状态。
- 确认商品数量不设 5,000 条上限；导出按全部已确认商品生成 Excel。
- 导出 POST 使用 15 分钟专用超时，避免默认 10 秒浏览器超时把后台已成功生成的批量文件误报为失败。
- 单件人工确认直接保存，不再显示或保存活动价、库存、发货、厂直、履约与依据等补充字段；这些非商品主数据列导出留空。
- “是否支持京东或者顺丰物流”不再由商品物流字段推导；无论模板是否保留历史映射，导出均留空，且新映射不再提供该项。

## 影响边界

- Alembic Revision：无。
- DeepSeek 调用、候选生成/确认规则和权限均不变。
- 导出 API 路径不变；允许的项目状态新增 `SELECTING`，不限制确认商品数量；前端导出请求超时为 15 分钟。
- 不新增确认字段、数据库列或项目级配置；现有历史映射保持可读，但非商品主数据不再提供为新映射项。

## 验证

- `apps/api-server/.venv/Scripts/python.exe -m pytest tests/recommendation/test_recommendation_export.py -q`：覆盖未完成选品的阶段性导出。
- `apps/api-server/.venv/Scripts/python.exe -m ruff check app/modules/recommendation/application/export_service.py app/modules/recommendation/infrastructure/repository.py tests/recommendation/test_recommendation_export.py`：通过。
- `apps/api-server/.venv/Scripts/python.exe -m mypy app/modules/recommendation/application/export_service.py app/modules/recommendation/infrastructure/repository.py`：通过。
- `npm run test -- --run src/views/bid/RecommendationWorkspaceView.spec.ts`：覆盖旧空快照晚到不能覆盖新完成候选，以及完成选品前且确认数超过 5,000 条时仍可导出。
- `npm run typecheck`：通过。
- `npm run build`：通过。

## 待验收

- 使用真实类型 4 项目完成一次推品，确认状态从处理中切至“待人工确认”后候选列表和数量无需刷新浏览器即可出现。
