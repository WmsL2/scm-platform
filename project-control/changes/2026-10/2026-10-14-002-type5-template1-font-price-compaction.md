# Type-5 模板 1 v5 字体、协议价与价格区压缩

日期：2026-10-14  
模块：Recommendation / Type-5 PPT  
状态：IMPLEMENTED / LOCAL VISUAL ACCEPTANCE PENDING

## 变更

- `JD_DETAIL_RED` v5 的“京东大客户价”读取冻结载荷 `prices.agreement_price`；缺值只清空动态值，不使用市场价或其他价格代替。
- 京东朗正体 玲珑 Run 同时声明 DrawingML `a:latin` 与 `a:ea`。渲染时也会修复既有私有运行模板克隆页，因此不需要覆盖已核验资产。
- 左右三行价格文本框依据保留样式的 14pt、1.5 倍行距，各回收一行即 21pt；品牌、分隔线、规格、包装、物流、定制说明和卖点等后续右栏组件同步上移 21pt。
- 动态换行仍在压缩后的几何基线上扩展；正式容量保护与 `PPT_V5_LAYOUT_PREVIEW` 诊断模式均保留。

## 数据合同

- 市场参考价：`prices.market_price`
- 京东大客户价：`prices.agreement_price`
- 服务层继续直接冻结 `candidate.price_snapshot`，未改变价格计算、数据库、API 或任务合同。

## 验证

- `pytest tests/recommendation/test_official_ppt_template_v5.py -q`：45 passed。
- `pytest tests/recommendation -q`：192 passed、5 failed；五项失败均为本地开发环境已将模板 1/2 默认切到仅支持单品的 v5，而旧测试仍假定四套业务模板默认 v3/支持组合及旧“协议价”标签，失败集合与上一轮一致，本次新增测试全部通过。
- `ruff check .`：通过；`mypy app`：139 source files 通过；`git diff --check`：通过。
- 使用 SHA-256 为 `58A568AADF5FE955811307601AEDD665DEC8614F02189DB7954098DC75B551D8` 的正式私有运行模板，经 `PptRenderer` 生成完全虚构 PPTX并重新打开：协议价 `¥ 321.50`、标签黑色、金额红色、14pt、1.5 倍行距、`a:latin`/`a:ea` 均正确；两列高度及后续组件偏移均为 21pt。
- 本机字体目录和字体注册表未发现“京东朗正体 玲珑”。未下载或分发字体；安装官方授权字体后的 WPS/Office 真实字形验收保留。

## 影响

- Alembic Revision：无。
- API / UI / Permission：无变化。
- 模板 2--5、历史 v3/v4、商品数据、价格计算和选品逻辑：无变化。
- 本机启动验证：未执行；按任务约束不启动服务、不创建真实业务任务。
