# Type-5 模板 1 v5 规格连续排版与价格纯数值显示

日期：2026-10-14  
模块：Recommendation / Type-5 PPT  
状态：IMPLEMENTED / LOCAL VISUAL ACCEPTANCE PENDING

## 变更

- `JD_DETAIL_RED` v5 在 PPT 展示边界将 `product_specification` 的 CRLF、LF 或 CR 分隔非空条目连接为连续段落；缺少现有分隔符时插入中文分号，已有中英文分号、逗号、顿号或句号时不重复添加。
- 规格值仍只读取冻结 `product.product_specification`；不修改数据库值，不改变条目中的文字、数字、单位或含义。
- 规格文本框显式开启自动换行、关闭自动缩字，保持微软雅黑 12pt、黑色、单倍行距和原宽度。动态高度及包装、物流、卖点等后续组件继续依据处理后的真实文本累计移动。
- 模板 1 的 `market_price` 与 `agreement_price` 只显示数值，移除展示层 `¥/￥`，仍统一保留两位小数；空值、标签与金额 Run 样式保持不变。

## 验证

- `pytest tests/recommendation/test_official_ppt_template_v5.py -q`：59 passed。
- 使用正式私有运行模板和 `PptRenderer` 生成并重新打开完全虚构 PPTX：四条规格为一个段落、无 CR/LF、自动估算两行且保持原 36.25pt 高度；市场参考价 `889.00`、京东大客户价 `699.50`，均无人民币符号。
- Alembic Revision：无。
- API / UI / Permission：无变化。
- 模板 2--5、历史 v3/v4、数据库、价格计算、图片和诊断模式：无变化。
- 本机启动验证：未执行；按任务约束不启动服务或创建真实业务任务。
