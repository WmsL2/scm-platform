# Change Record: All Excel Imports Navigation Lock

Date: 2026-09-21
Branch: `fix/product-import-preview-navigation-lock`
Alembic Revision: None

## Problem

现有 Excel 上传、解析和确认导入依赖当前浏览器请求同步等待。用户在处理期间切换站内页面、刷新或关闭页面，可能中断请求并误以为导入已经在后台继续执行。该风险不只存在于商品导入，也存在于供应商、类目和投标项目 Excel 入口。

## Change

- 新增前端通用 Excel 导入导航锁，集中管理全屏加载、路由守卫、`beforeunload` 和资源清理。
- 覆盖当前全部 4 个 Excel 入口：商品主数据、供应商、类目、投标项目创建。
- 商品和供应商同时覆盖上传预览与 Confirm；类目覆盖原子导入请求；投标项目覆盖 Excel 上传、建项和解析请求。
- 处理期间启动 Element Plus 全屏加载遮罩，锁定页面滚动和点击，并阻止 Vue Router 站内离开。
- 刷新或关闭页面时请求浏览器显示原生离开确认。
- 在请求成功、失败或超时后的 `finally` 中统一解除锁定；组件卸载时清理事件监听和残留遮罩。
- 状态判断和浏览器离开保护保留为纯函数，并由前端单元测试覆盖。

## Boundary

本次只提供紧急上线阶段的前端防误操作保护。导入请求仍依赖当前页面和 Web 进程，不具备断线续跑、后台任务查询、跨页面进度恢复或服务重启恢复能力；这些能力应在后续异步任务化中单独实现。

## API / UI / Permission

- API: 无变化。
- UI: 全部 Excel 导入请求期间新增统一全屏遮罩、站内导航拦截和刷新/关闭提醒。
- Permission: 无变化，各入口继续使用原有权限。

## Verification

- 前端单元测试覆盖空闲与处理中两种离开行为。
- 执行前端完整单元测试、TypeScript 类型检查和生产构建。
