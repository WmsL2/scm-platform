# 2026-09-22-009：供应商导出与下载模板对齐

- Supplier Import 下载模板与 Supplier Export 复用同一 Excel 模板工厂：Sheet 为“供应商导入”，固定五列表头、表头样式、列宽、冻结首行、自动筛选与电话文本格式一致。
- Export 仅输出供应商名称、主营品牌、主要优势、有效联系人和联系电话；多联系人/电话按相同顺序以中文分号拼接。
- Export 保持 selected supplier_ids、跨页选择和 stale-selection 校验；不输出编码、归档/合作状态、时间或审计字段。
- 无 Migration、无 Permission 变化。
