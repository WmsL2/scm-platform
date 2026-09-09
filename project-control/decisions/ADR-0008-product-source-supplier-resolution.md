# ADR-0008：Product Source Supplier Resolution

状态：ACCEPTED
日期：2026-09-09

## 背景

商品大表已经是正式 Product 的来源，但其中“供应商”列原先被限定为 IMPORT_ONLY，不能形成 Product 到 Supplier 的关系。业务现确认该列表示该大表行的来源供应商；Supplier Master 必须先完成导入。

## 决策

- Excel 原始供应商名称保存到 Product Import Staging 的 `supplier_name_raw`，只用于审计、排障和解释匹配；它不是业务外键。
- 正式 `scm_product` 保存 `source_supplier_id CHAR(36) NOT NULL`，建立索引及 FK → `scm_supplier.id ON DELETE RESTRICT`。该字段不唯一，且不得命名为普通 `supplier_id`。
- `source_supplier_id` 表示来源供应商，不表示该商品唯一供应商，也不表示存在 Supplier Product Quote；Product Import 不自动创建报价。
- 自动匹配只允许 Unicode NFKC、trim 和连续空白压缩。标准化名称严格相等且恰有一个 `ARCHIVED + NORMAL + not deleted` 候选时才自动写 `MATCHED/NAME_EXACT`；不使用 AI、模糊或简称规则。
- `AMBIGUOUS`、`UNMATCHED`、`INELIGIBLE` 必须人工解析，且只能选择当前有效 Supplier Master，不能在商品导入中创建或改变供应商状态。
- 一个 `import_task_id + supplier_name_normalized` 只有一个 Match Decision；推荐独立 `scm_product_import_supplier_match` 表，并由 Import Row 关联该决策。
- Confirm 必须以全批次原子事务执行，并重新验证所有行/类目/价格、所有决策及每个已匹配供应商当前 eligibility；状态在匹配后变化时 Confirm 必须失败。

## 结果

正式 Product 获得可审计、稳定的来源供应商关联，同时 Supplier Product Quote 保持独立历史报价领域。本 ADR 仅冻结文档和 Schema 决策；未创建 Migration、ORM、API 或 UI。
