# ADR-0010：商品大表导入直接保存类目与价格正式值

状态：ACCEPTED
日期：2026-09-10

## 背景

业务确认公司固定商品大表中的一级、二级、三级类目和所有价格/毛利字段均是已经整理、填写完成的正式商品数据。导入不应以类目预加载为前置条件，也不应以系统公式重算后覆盖或拦截 Excel 的已确认金额。

## 决策

- Product Import 不加载、不解析、不校验 `scm_category`，也不以类目路径生成 `category_id`；一级、二级、三级类目原文直接保存到正式 `scm_product`。
- `scm_product.category_id` 调整为可空的保留关联字段，供未来有正式受控类目域时使用；它不是本期固定商品大表 Confirm 的前置条件。
- Product Import 直接保存 Excel 的价格、毛利、折扣率和价格虚高比例。导入只做 Decimal 格式校验，不执行 Pricing Service、不做公式一致性校验、不改写 Excel 价格。
- `cost_price` 仍是正式 Product 的当前成本价；因正式表为非空字段，导入必须有可解析的成本价。其他价格列依照正式表的可空性保存。
- Pricing Service 保留给现有“单独更新当前成本价”操作；该操作因只输入成本价而需要系统重算，和固定商品大表导入是不同业务场景。
- 来源供应商规则不变：Excel 原值只入 Staging，正式 Product 仍通过已匹配有效 Supplier Master 的 `source_supplier_id` 关联。

## 结果

固定模板可在没有 Category Source Loader、没有 `scm_category` 数据的环境中直接预览和 Confirm。供应商为空、未匹配或失效仍然会阻止整个批次确认；模板、数值格式和全批次原子事务规则继续有效。

## Supersedes

- 对 Product Import 场景，替代 ADR-0008 中“Confirm 重新校验类目和价格”的部分。
- 对 Product Import 场景，替代 `docs/data-gates/category-pricing-rules.md` 与 Product/Category/Pricing Schema Review 中“类目解析及导入时公式重算”的部分。
- 不替代 ADR-0009 关于单独成本价更新使用 Pricing Service 的决策。
