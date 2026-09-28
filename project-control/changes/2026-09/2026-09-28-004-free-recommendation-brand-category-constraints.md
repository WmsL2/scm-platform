# Change Record：自由推品明确品牌与语义类目筛选

日期：2026-09-28  
分支：`codex/feat/free-recommendation-brand-category`

## 变更

- Type-4 新 Run 的 Requirement 版本升级为 `v5`。
- 客户使用“必须、仅限、指定、只要”等强制语气指定品牌时，Agent 写入 `required_brands`，数据库按商品品牌大小写无关的包含匹配进行硬筛选；普通品牌提及不筛选。
- 客户明确指定类目时，Agent 写入原始类目词和 `category_intents` 近义词；数据库在商品一级、二级、三级类目中按任一词匹配，使需求类目与商品受控类目名称不完全一致时仍可召回。
- 场景、用途、节日、人群、数量、库存、物流、资质和价格有效期继续忽略，不参与筛选或排序。
- 工作台需求摘要显示指定品牌和指定类目，避免将实际筛选条件隐藏在原始需求文本中。

## 数据库与兼容性

- Alembic Revision：无。复用既有 Run 的 `parsed_requirement` JSON 字段。
- 仅 `v5` Run 启用品牌硬筛选与语义类目词；历史 V3/V4 Run 的解析 JSON 与筛选语义保持不变。

## 验证

- 后端：Ruff、Mypy，以及 Agent 解析/适配、核心候选筛选测试。
- 前端：TypeScript 类型检查和自由推品工作台 Vitest。
