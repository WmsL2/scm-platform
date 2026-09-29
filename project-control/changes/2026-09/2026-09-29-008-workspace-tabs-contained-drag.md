# 2026-09-29 工作区标签栏内浏览器式拖拽

## 目标

将顶部工作区标签的拖动反馈调整为接近浏览器标签栏：被拖动的完整标签跟随鼠标，其他标签在同一行内依排序动画让位；拖动视觉不得进入页面内容区。

## 实现

- `WorkspaceTabs` 使用标签栏专用 Pointer Event 拖动逻辑，不再依赖仅在容器命中区域内排序的 SortableJS fallback。
- 鼠标移动超过 4px 后创建完整标签预览；预览始终固定在标签栏的纵向中心，横向坐标夹在标签栏左右边界内。
- 指针监听注册在 `document`：即使鼠标移到标签栏外，仍按当前横坐标持续更新标签位置与排序。
- 通过 FLIP 位移动画让未拖动的标签平滑横向让位；拖动开始时直接以内联强制样式隐藏原标签但保留空间，页面仅显示完全不透明、跟随鼠标的完整标签预览。松开鼠标后清理隐藏样式并写入 Pinia 的用户排序偏好；取消拖动会恢复原顺序。
- 保留关闭按钮过滤与当前浏览器内的标签顺序持久化。
- 激活标签底部左右外角使用无阴影的径向渐变圆弧与内容区连接，不改动标签自身的完整底边圆角或叠加额外边框。

## 影响

- API：无变化。
- Permission：无变化。
- 数据库 / Alembic：无变化。
- UI：仅顶部工作区标签拖动视觉与边界约束调整。

## 验证

- `npm --prefix apps/web-admin run typecheck`
- `npm --prefix apps/web-admin run test -- --run src/components/layout/WorkspaceTabs.spec.ts`
- `npm --prefix apps/web-admin run test -- --run`（40 files / 165 tests passed）
- `npm --prefix apps/web-admin run build`
