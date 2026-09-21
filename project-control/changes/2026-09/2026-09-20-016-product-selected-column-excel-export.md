# 2026-09-20-016：商品自选字段 Excel 导出

- Product List 支持跨页勾选商品并选择导出的 Product Master 字段。
- 新增受 `product:list` 保护的同步 Excel 导出接口；导出仅限允许的 43 个业务字段，保留请求商品顺序和标准字段顺序。
- 选择“图片”字段时，系统托管的 `local-media/...` 引用会转换为存储 key 后读取，并以 XlsxWriter `embed_image()` 的 Excel Place in Cell / richData 方式嵌入 XLSX，不再使用浮动 Drawing。图片放入 80×80 透明 canvas，水平垂直居中、保持比例；大图缩小，小图不放大。外部 URL 不主动抓取，缺失或损坏图片同样留空而不影响整批导出。新增正式依赖 `XlsxWriter>=3.2,<4`；Excel 365 新版本支持该能力，较旧版本可能不完整支持。
- 导入预览类目路径忽略空层级；ADR-0033 与正式页面规则已同步。
- 商品列表保留表头仅选择当前页的行为，并增加“全选全部商品（N）”：通过受 `product:list` 保护的 `GET /api/v1/products/selection-ids` 按当前筛选条件取得真实可见 Product ID，跨页选择可回显和局部取消。
- `selection-ids` 与 Product List 复用相同筛选、供应商可见性和稳定排序；结果超过 5,000 条明确返回 422，不静默截断。
- 无数据库 Migration。
