# 2026-09-24 自由推品模板映射交互修复

## 背景

原页面以商品字段为左侧固定项、要求运营手工输入模板列名，无法直观看到不同上传模板的真实表头，也容易理解反映射方向。项目列表筛选控件布局异常，文件上传区还同时显示 Element Plus 默认文件列表和自定义文件名。

## 变更

- 新增推荐模板结构只读接口，按项目、模板文件、Sheet 和表头行返回真实工作表列表及非空表头。
- 映射页面调整为左侧只读“上传模板列”，右侧可搜索选择商品主数据 43 个正式字段或人工“是否厂直”。
- 正式列名相同的字段自动匹配；一个商品字段只能选一次；重复模板表头明确提示并禁止映射。
- 前端提交时转换回既有 `商品字段 key -> 模板表头` JSON，未改变数据库映射合同和导出方向。
- 新创建候选冻结完整可导出商品字段与供应商名称；历史候选不回查当前商品补值。
- 修复投标项目列表筛选布局；上传控件仅显示一份文件名，并提供移除操作。
- 修复推荐导出创建后立即下载的 404 竞态：导出写事务改为在 POST 响应发送前提交，避免浏览器紧接着下载时查不到刚生成的导出记录。

## 接口 / UI / 权限

- 新增 GET `/api/v1/bid-projects/{project_id}/recommendation-templates/{file_id}/structure`。
- 接口复用 `recommendation:create`，无新权限。
- 模板映射 PATCH 与导出接口合同不变。
- 推荐导出和下载 URL 不变；仅收紧 POST 导出的事务提交时点。

## 数据库

- Alembic Revision：无。
- 无 Schema 变化。

## 验证

- Backend Ruff：通过。
- Backend mypy（Bid / Recommendation）：通过。
- Recommendation 相关后端测试：10 passed。
- Web TypeScript typecheck：通过。
- Web 定向 Vitest：12 passed。
- Backend 全量 pytest：256 passed（含导出响应前提交的回归约束；结束清理 Windows pytest 临时目录时出现权限告警，不影响测试退出结果）。
- Web 全量 Vitest：137 passed。
- Web 生产构建：通过；仅保留既有大 chunk 告警。
- 后端应用导入启动检查：通过（`Zhongcheng SCM Platform`）。
