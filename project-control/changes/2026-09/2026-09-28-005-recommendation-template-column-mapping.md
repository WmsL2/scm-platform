# Change Record：自由推品模板列号映射

日期：2026-09-28  
分支：`codex/feat/recommendation-template-column-mapping`

## 变更

- 推荐模板映射由旧版 `字段 key -> 唯一表头` 扩展为 V2 `列号 -> 字段 key` 列表。
- 重复模板表头不再禁用：每个物理列可独立选择字段，同一个商品字段可重复选择并写入多个模板列。
- 自动映射按上传表的每个列号生成；导出按物理列号写入，避免重复表头覆盖。
- 旧映射合同保留读取与导出兼容；旧合同遇到重复表头仍要求运营重新确认以消除歧义。

## 数据库与接口

- Alembic Revision：无。复用 `scm_recommendation_template_mapping.mapping_json` JSON 列。
- 模板映射 PATCH 与读取响应的 `mapping_json` 支持旧合同和 V2 合同；无 URL、权限变更。

## 验证

- 后端定向模板合同与导出测试：14 passed。
- 后端 Ruff、Mypy：通过。
- 前端类型检查、工作台 Vitest（5 passed）、生产构建：通过；仅有既有大 bundle 警告。
