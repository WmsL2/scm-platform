# 2026-09-24-001：商品导出使用 WPS DISPIMG 单元格图片

- 商品自选字段 Excel 导出选择“图片”时，改为为每个有效图片生成唯一的 WPS `DISPIMG` 公式，并将图片写入 XLSX 的 `xl/media/`、`xl/cellimages.xml` 与对应关系文件。
- 导出不再使用 Excel Rich Data / Place in Cell，避免不支持该格式的 WPS 客户端直接显示底层 `#VALUE!` 占位值。
- 继续保留图片单元格边框、居中、行高、列宽、自动筛选、导出字段顺序和图片缺失时留空的行为。
- WPS `DISPIMG` 是 WPS 扩展格式；Microsoft Excel 或不支持该函数的软件可能显示公式或公式错误，不作为通用 Excel 图片格式承诺。
- Alembic Revision：无。API、UI、权限和商品数据均无变化。
