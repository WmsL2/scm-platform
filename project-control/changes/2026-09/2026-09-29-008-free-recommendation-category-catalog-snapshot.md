# Change Record：自由推品真实类目清单快照

日期：2026-09-29  
分支：`codex/feat/recommendation-category-catalog-snapshot`

## 变更

- Type-4 新 Run 升级为 Requirement V8：需求解析只保存客户明确类目原词，不再把模型生成的 `category_intents` 用于商品查询。
- 解析后，后端按当前可推荐商品、供应商状态和非类目硬条件生成所有真实一级、二级、三级节点及候选数，冻结在 Run 的 JSON 快照中。
- Agent 第二次结构化调用只返回后端发放的 `category_key`；未知 key 被拒绝，真实选中节点保存到已有的类目选择记录。
- 选中一级自动展开其所有下级，选中二级自动展开其所有三级路径，选中三级才精确筛选。明确类目无匹配时进入 `NO_CANDIDATES`，不回退到全库。
- 工作台展示本 Run 已冻结的真实类目树节点数量。

## 数据库与兼容性

- Alembic Revision：`20260929_0042`，新增 `scm_recommendation_run.category_catalog_snapshot` JSON 可空列。
- V3–V7 Run 保持原有查询和展示语义；仅新创建的 V8 Run 使用真实类目树机制。

## 验证

- 后端 Agent/适配/核心服务推荐测试：通过。
- 后端 Ruff、Mypy：通过。
- 前端类型检查和生产构建：待本分支最终验证。
