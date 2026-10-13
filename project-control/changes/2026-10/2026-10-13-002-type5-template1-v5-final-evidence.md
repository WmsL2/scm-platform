# Change Record：模板 1 v5 第二轮验收证据

日期：2026-10-13
模块：recommendation
状态：IMPLEMENTED / PRIVATE EVIDENCE GENERATED

## 卖点展示格式

客户模板第 2 页的“产品卖点（介绍详细）”提供六个自动填入行位；第 3 页人工成品以连续 `1、…` 编号展示非空卖点，首项允许自然换行续写。该编号属于固定展示格式。

- 渲染器将最多六个非空换行卖点依次写成 `1、` 至 `6、`；输入中已有的数字编号会被移除并重新编号，避免重复。
- 空行被忽略；没有卖点时仅保留固定标题，不生成空编号行。
- 所有卖点段落继续使用客户规定的微软雅黑、12pt、黑色、单倍行距。

## 私有证据样例

在 Git 忽略的 `.codex-assets/official-ppt/samples/v5/` 重新生成五份既有样例，并新增：

- `JD_DETAIL_RED-v5-fictional-customer-price-evidence.pptx`：纯渲染器虚构金额 `¥ 321.00`；固定标签黑色、金额 Run 14pt 红色且同段展示，不增加业务字段来源。
- `JD_DETAIL_RED-v5-fictional-supplement-layout-evidence.pptx`：三张颜色和比例均不同的虚构补图；验证左、中、右竖版槽的顺序、间距、坐标与居中 cover 裁剪。
- `JD_DETAIL_RED-v5-fictional-main-image-fit-evidence.pptx`：分别以包含商品主体的横图和竖图验证主图居中裁剪；横图左右对称裁剪、竖图上下对称裁剪。

所有内容仅使用虚构数据和私有运行资产；不写入客户原件，也不纳入版本控制。

## 影响

无 Alembic Revision、数据库、API、UI、权限、业务报价或推荐规则变化。v3/v4 和模板 2--5 保持不变。
