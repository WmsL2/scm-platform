# ADR-0038：自由推品确认结果导出合同

状态：ACCEPTED  
日期：2026-09-23

## 背景

ADR-0037 建立了自由推品的模板、Run、候选和人工确认底座，但当时没有“确认结果导出文件”审计记录，也无法表达“是否厂直”的人工结论。普通投标项目的 `BidProjectService.export` 依赖需求行、人工选品及报价状态，不能用于类型 4。

## 决策

- 新增 Migration `20260923_0040`，仅为自由推品增加 `scm_recommendation_export` 和 `scm_recommendation_confirmation.factory_direct`；本 ADR 是 ADR-0037 中“后续 B/C 不新增 Migration”约束的明确例外与补充。
- `factory_direct` 只能由人工确认填写 `PENDING`、`YES` 或 `NO`；未确认时导出值为“待确认”，系统和 AI 均不得推断。
- 导出仅允许 `CONFIRMED` 或 `EXPORTED` Run，且至少存在一条确认记录；未确认候选绝不写入结果文件。
- 导出从当前最新、已确认的 `RECOMMENDATION_TEMPLATE` 读取工作簿，保留工作表、标题、单元格样式、数据起始行和公式模板；再次核验映射表头，模板被替换或映射失效时返回 409。
- 每次导出创建 `RECOMMENDATION_EXPORT` 附件和独立 `scm_recommendation_export` 审计记录，保存模板/映射引用及映射快照；项目内附件版本号连续递增，导出文件只允许经对应 Run 下载。
- 导出文件存储成功但数据库事务异常时补偿删除对象；不改写 Product、Supplier、候选快照或原模板。
- 权限复用已预置的 `recommendation:export`，不增加新的权限码。

## 后果

- 历史 Run 导出时使用导出当刻的最新已确认模板；导出记录保留实际使用的模板和映射快照，后续模板升级不会改写已有导出。
- 当前导出是同步生成；超大模板或超多确认候选的异步化属于后续性能议题，不在本次范围。
