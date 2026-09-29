# ADR-0045：自由推品真实类目清单快照

状态：ACCEPTED  
日期：2026-09-29

## Context

Type-4 Requirement V5/V6 允许 Agent 生成 `category_intents` 同义/近义词，再在正式商品三级类目文本中模糊匹配。模型可能生成与客户需求无关的词，造成商品误召回；同时，普通 `scm_category` 维表不是 Product Master 的受控外键，不能代表当前存在且可推荐的商品类目。

## Decision

- Type-4 新 Run 使用 Requirement V8。第一次模型调用只提取客户明确写出的原始类目词；`category_intents` 必须为空，禁止模型生成近义词进入商品查询。
- 后端先依据正式 Product `ACTIVE`、来源 Supplier `ARCHIVED + NORMAL + 未删除`，以及本次价格、折扣、点位、强制品牌等非类目硬条件，聚合实际存在的三级商品路径及候选数量，并生成一级、二级、三级树节点。
- 后端将完整清单保存到该 Run 的 `scm_recommendation_run.category_catalog_snapshot` JSON 列。该快照不是磁盘临时文件；每个新 Run 重新生成，历史 Run 不回写。
- 第二次模型调用只能从快照中的 `category_key` 选择直接相关的节点。宽泛类目应选择一级节点，二级类目应选择二级节点，具体类目才选择三级节点；服务层拒绝不属于快照的 key，并将实际选中的节点冻结到既有 `scm_recommendation_category_choice`。
- V8 最终候选查询按已冻结节点展开：一级匹配其全部下级，二级匹配其全部三级路径，三级精确匹配；客户明确提出类目而模型没有选中任何真实节点时，本 Run 为 `NO_CANDIDATES`，不得回退到全库或使用模型生成的近义词模糊查询。
- V3–V6 Run 的解析 JSON、查询行为和历史候选保持不变。

## Consequences

- “可推荐类目”仅表示存在至少一件当前满足可验证硬条件的正式商品；库存、履约、活动价等无正式可验证字段的事实仍须人工确认。
- 新增 Alembic Revision `20260929_0042`，为 Run 增加可审计的 JSON 快照列。
- Agent 每个有明确类目需求的 V8 Run 增加一次受控的结构化类目匹配调用，但模型不会读取数据库或自行编造用于 SQL 的类目词。

## Related

- ADR-0026：商品主数据与类目维表脱钩
- ADR-0042：自由推品明确品牌与语义类目硬筛选（V8 对其类目近义词路径的替代）
- ADR-0044：自由推品类目分配文本识别
