# Change Record：隐藏类型 5 旧人工组套入口

日期：2026-10-12
分支：`codex/fix/hide-legacy-manual-package`
模块：recommendation

## 背景

当前类型 5 `COMBINATION` Run 已以人工确认的 AI 组合卡作为 PPT 组合页来源。“额外人工组套”是旧流程的兼容入口，在新工作台中仍可见，容易让用户以为其会参与当前 PPT 输出。

## 变更

- 从类型 5 工作台隐藏“额外人工组套”卡片、创建按钮和手动组套弹窗。
- 工作台不再加载旧人工组套列表，避免无效请求和误导性空态。
- 保留历史人工组套数据库记录、后端接口和历史渲染兼容逻辑；不删除历史数据。
- 组合 Run 继续以已确认 AI 组合生成 PPT，单品 Run 行为不变。

## 数据库 / 接口 / 权限

- Alembic Revision：无。
- API 与 Permission：无变化；仅当前工作台不再调用旧人工组套接口。

## 验证

- `npm run test -- --run src/views/bid/PptSolutionWorkspaceView.spec.ts`：2 passed。
- `npm run typecheck`：通过。
- `npm run build`：通过。
