# 2026-09-24 工作区标签拖拽排序

## 目标

允许用户拖动 Web Admin 顶部已打开的工作区标签，将常用页面调整到靠前位置，并在当前浏览器保留顺序偏好。

## 实现

- `WorkspaceTabs` 采用 SortableJS 官方横向排序能力，并锁定仅 `.el-tabs__item` 可排序。
- 开启 `forceFallback` 与 `fallbackOnBody`，以跟随鼠标的浮层替代浏览器原生 HTML5 拖放，避免越过标签边界时出现禁止标志。
- 使用 `swapThreshold` 与 `invertSwap` 提供连续的前后换位反馈；拖动开始时直接给原列表标签添加独立的全局占位类，显示完全不透明的深蓝等宽虚线占位块。手动占位类与 SortableJS 内部管理的 `ghostClass` 使用不同名称，避免非激活标签换位时内部 ghost 类被移除而丢失背景。全局高优先级样式覆盖激活及非激活标签的默认背景；经过其他标签时通过排序动画将两侧标签挤开，半透明拖动浮层继续跟随鼠标。
- 为避免 Element Plus 或 SortableJS 在首次换位后重设 class，拖动开始及每次 `onMove` 都会向原标签重新写入带 `important` 的占位内联样式；结束或组件卸载时完整清理，不使用可能提前清理状态的 `onUnchoose`。
- 关闭图标通过 `filter` 排除在拖动触发区域之外，保持原有关闭行为。
- `workspace` Pinia Store 提供受控 `moveByIndex` 操作，保存去重后的路径顺序，最多保留 100 个路径。
- 页面刷新后不主动恢复已经关闭的业务页面；当页面再次打开时，按保存的顺序偏好插入。
- 登出和改密仍调用既有 `reset` 关闭业务标签，但不会删除无敏感信息的排序偏好。
- 本地存储不可用或内容损坏时安全回退到当前会话内排序。

## API / UI / Permission

- UI：顶部工作区标签增加平滑横向拖拽、越界换位与拖动浮层反馈。
- API：无变化。
- Permission：无变化。
- Alembic Revision：无。

## 依赖

- 新增运行依赖：`sortablejs`。
- 新增开发依赖：`@types/sortablejs`。
- 参考实现：SortableJS 官方仓库及其 Vue 3 官方组件仓库；本项目直接绑定 Element Plus 标签导航节点，以保持现有 Tab 结构与路由行为不变。

## 验证

- `npm run typecheck`：通过。
- 定向 Vitest：2 files / 4 tests passed。
- 全量 Vitest：34 files / 142 tests passed。
- `npm run build`：通过；仅保留既有的大 chunk 告警。
