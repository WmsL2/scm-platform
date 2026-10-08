# Change Record：类型 5 方案选择持久化与高亮

日期：2026-10-08
分支：`fix/type5-compact-plan-refs`

## 变更

- 新增方案选择接口，在同一事务中确认方案商品并记录方案选择状态。
- 方案列表增加 `is_selected`、`selected_by`、`selected_at`。
- 工作台对已选方案使用绿色边框、浅绿色背景和“已选方案”标签，刷新及重新进入后继续显示。
- 已选方案按钮显示“已选择此方案”并禁用，方案详情弹窗同步显示该状态。
- 当前允许累计选择多张方案，不自动撤销其他方案或既有商品确认。

## 数据库与接口

- Alembic Revision：`20261008_0047`。
- 新增 `POST /api/v1/ppt-solution-projects/plans/{plan_id}/select`。
- 权限：沿用 `recommendation:review`，无新增权限码。

## 验证

- 推荐模块测试：68 passed。
- Ruff：通过。
- Mypy：通过。
- 前端类型检查：通过。
- 类型 5 工作台测试：1 passed。
- 前端生产构建：通过。
- 本机数据库已升级到 `20261008_0047`。
- 浏览器手工视觉验收待执行。
