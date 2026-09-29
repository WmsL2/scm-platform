# Change Record：自由推品类目分配文本识别

日期：2026-09-28  
分支：`codex/feat/recommendation-template-column-mapping`

## 变更

- Requirement V6 识别明确的“类目 + 数量”业务表达，以及“需要水杯、保温杯、随行杯”等直接商品类目表达，将其中的类目名称视为明确类目要求。
- 家电、厨具、日用等类目通过商品一级、二级、三级类目中的语义词过滤，全部符合硬条件的商品都会入池。
- 数字不会查询或扣减库存、不会创建订单，也不会限制候选数量；所有数量仍保持忽略。
- 工作台在“筛选：指定类目”展示解析后的类目名称，运营可核对 Agent 的理解结果。

## 数据库与接口

- Alembic Revision：无。复用 Recommendation Run 的 `parsed_requirement` JSON。
- 既有 Run API 不新增必填字段；无 URL、权限变更。

## 验证

- 后端推荐模块测试：55 passed。
- 后端 Ruff、Mypy：通过。
- 前端类型检查、工作台 Vitest（6 passed）、生产构建：通过；仅保留既有大 bundle 警告。
