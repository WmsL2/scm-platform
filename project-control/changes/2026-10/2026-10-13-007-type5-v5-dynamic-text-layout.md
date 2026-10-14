# Change Record：Type-5 模板 1、2 v5 动态文本纵向联动

日期：2026-10-13

## 范围

- 仅调整 `JD_DETAIL_RED` v5 与 `JD_FESTIVE_RED` v5 的克隆输出页文本布局。
- 不修改私有运行资产、客户原件、模板 3--5、历史 v3/v4、API、数据库、价格或选品规则。

## 变更

- 动态字段按实际文本框宽度、Run 字号、段落行距、内边距和显式换行计算所需行数及高度。
- 模板 1 按标题、参考/价格并列区、品牌、规格、包装、物流、卖点的原有顺序累计扩展；下方右侧关联形状保持原间距下移。
- 模板 2 保留固定属性框和标签。动态值层缩为各自原预留间隙并在该间隙内换行；首行扩展下移 SKU 固定行，SKU/第二行扩展下移卖点、说明、装饰和三张补图。
- 页面底部空间不足时返回 `PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED`，携带商品标识、字段和所需额外高度；不截断、不缩字、不生成越界页面。

## 验证

- 虚构 PPTX 夹具测试覆盖一至多行标题、混合 SKU、标题与 SKU 累计下移、卖点换行、固定标签/字体和图片槽保留、页面边界受控失败。
- `pytest tests/recommendation/test_official_ppt_template_v5.py tests/recommendation/test_official_ppt_template_festive_v5.py -q`：66 passed。
- 定向 Ruff、Mypy 和 `git diff --check` 通过。

## 未完成

- 未启动服务、未创建真实业务任务、未用真实商品数据渲染。
- 仍需用户以指定字体的 Office/WPS 对本地生成结果进行最终视觉验收。
