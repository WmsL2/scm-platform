# Type-5 模板 1 v5 动态属性实际行高校准

日期：2026-10-14  
模块：Recommendation / Type-5 PPT  
状态：IMPLEMENTED / WPS RENDER VERIFIED / CUSTOMER ACCEPTANCE PENDING

## 根因

模板 1 的自动换行行数估算已使用与写入 PPT 相同的连续规格文本、文本框有效宽度和固定标签，但高度模型把微软雅黑 12pt 单倍行距当作 12pt/行。WPS 对正式私有模板的 `TextRange.BoundHeight` 实测为 14.4pt/行，因此每个可见行少分配 2.4pt。5 行规格少 12pt，9 行少 21.6pt，包装清单仍按低估后的高度定位，造成可见文本重叠。

## 修复

- 模板 1 的公共段落度量使用字体自然行框 `字号 × 1.2`，并与段落显式行距取较大值；14pt、1.5 倍行距等既有字段仍保留其较大行距。
- 文本高度继续计入真实左右/上下内边距，并增加 0.5pt 跨 Office/WPS 安全余量。
- 拉丁宽字符集合补充小写 `m/w`，减少中英文、数字、单位混排的宽度低估。
- 既有动态布局继续按原始坐标与每个字段的新增高度累计一次；包装、物流、固定定制说明、卖点、分隔线和装饰随前置字段增长同步移动。
- 规格连续段落、中文分号、微软雅黑 12pt、黑色、单倍行距、原宽度、正式容量拒绝与诊断模式均保持。

## WPS 实测

- 客户示例型两行规格：文本框 36.5pt，WPS 可见文本 28.8pt，包装顶部与规格可见底部间隔 1.51pt。
- 五行规格：旧算法 67.2pt，修复后 79.7pt；包装、物流和后续组件额外下移 12.5pt，间隔 1.51pt。
- 九行规格：旧算法 115.2pt，修复后 137.3pt；后续组件额外下移 22.1pt，间隔 1.51pt。
- 规格、包装、物流同时换行：WPS 形状高度分别为 50.9pt、50.9pt、36.1pt，可见文字与下一组件均无重叠。
- 十行规格在正式模式返回 `PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED`；`PPT_V5_LAYOUT_PREVIEW` 继续生成诊断文件。

私有诊断 PPTX 与 WPS PNG 位于 Git 忽略目录 `.codex-assets/official-ppt/samples/v5/jd-detail-red-layout-diagnostic/`，未修改客户原件或正式运行模板。

## 验证

- `pytest tests/recommendation/test_official_ppt_template_v5.py -q`：62 passed。
- `ruff check .`：通过。
- `mypy app`：139 source files 通过。
- `git diff --check`：通过。
- Alembic Revision：无。
- API / UI / Permission：无变化。
- 模板 2--5、历史 v3/v4、数据库、价格、图片和诊断模式合同：无变化。
- 本机服务启动：未执行；按任务要求不启动前后端或创建真实任务。
