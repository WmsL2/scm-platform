# Change Record：供应商主体名称统一判重

Change ID：2026-09-22-007
Module：supplier
Branch：`fix/supplier-name-normalized-dedup`
Date：2026-09-22

## 内容

- 新增与商品来源严格匹配分离的 Supplier Master 主体名称键。
- 手工新增/改名、Excel 预览/确认统一以该键判重；确认重新检查，避免预览后新增同名仍入库。
- Excel 内同键重复按原行号提示；纯标点名称失败；原名称和供应商 ID 不自动变更。
- 复用逻辑删除记录仅在主体键唯一时进行，多条候选拒绝自动恢复。

## 影响

- Alembic Revision：无；正式字段和权限无变化。
- API 路径、请求体无变化；预览逐行错误及创建/编辑/确认 `409 SUPPLIER_NAME_EXISTS` 适用于标点差异重名。
- UI 无代码变化，显示后端已有错误消息。
- 关联 ADR：ADR-0036；不改变 ADR-0008 的商品来源供应商匹配。

## 验证

Supplier 名称键单测及供应商 API 集成测试覆盖中英文括号、空格、标点、Excel 内重复、预览/确认时间差、改名冲突和逻辑删除恢复。
