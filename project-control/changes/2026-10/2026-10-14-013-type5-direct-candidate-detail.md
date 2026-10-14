# 类型 5 单品推品商品详情弹窗

日期：2026-10-14  
分支：`codex/task-cancel-delete`  
状态：IMPLEMENTED / BROWSER_ACCEPTANCE_PENDING

## 完成内容

- 类型 5 的单品推品候选表最右侧新增固定“操作”列，提供“查看详情”。
- 单品候选与组合方案商品共用同一个只读详情弹窗，避免两处字段和展示口径漂移。
- 弹窗只读取当前 Recommendation Run 冻结的商品和价格快照，展示图片、SKU、品牌、型号、三级类目、商品名称、规格、卖点、成本价、毛利率、协议价、京东价、折扣率和好评率；不额外请求商品主数据，也不写入任何数据。

## 接口与数据库

- Alembic Revision：无。
- API：无新增或变更。
- 权限：无新增或变更；详情只在已可见的类型 5 候选表内打开。

## 验证

- 前端定向 Vitest：`npm test -- --run src/views/bid/PptSolutionWorkspaceView.spec.ts`，2 passed。
- 前端完整 Vitest：`npm test -- --run`，45 文件 / 197 项 passed。
- 前端类型检查：`npm run typecheck`，通过。
- 前端生产构建：`npm run build`，通过；仅保留既有主 bundle 超过 500 kB 的 Vite 提示。
- 真实浏览器点击、弹窗字段和图片预览仍需在本机前端刷新后以实际类型 5 单品 Run 验收。

## 边界

- 不改变 AI 推品、人工确认、PPT 生成、组合推品、商品主数据、价格计算或任务队列行为。
- 本次不自动提交、推送或创建 PR。
