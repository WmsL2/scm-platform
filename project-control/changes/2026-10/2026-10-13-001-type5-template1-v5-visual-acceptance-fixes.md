# Change Record：模板 1 v5 第一轮视觉验收修复

日期：2026-10-13
模块：recommendation
状态：IMPLEMENTED / PRIVATE DESKTOP RENDER REVIEW PENDING

## 范围

仅修复私有 `JD_DETAIL_RED` v5（模板 1）的标准化、渲染和测试。未修改客户原始 PPT、v3、v4、模板 2--5、选品、报价、API、权限、数据库或 Migration。

## 修复

- 品牌框使用客户第 3 页已验证的几何：`left=6.379in`、`top=2.615in`、`width=6.299in`、`height=0.301in`；其下 `3.082in` 虚线不再与品牌字段相交。
- “京东大客户价：”固定标签保持客户原有的 14pt 黑色；仅 `{{jd_customer_price}}` Token Run 保持 14pt 红色。当前没有可靠冻结来源，运行期继续填空值，不以任何业务价格代替。
- 商品规格、包装清单、发货物流、产品卖点（标题和动态值）使用单倍行距；品牌、参考价、价格和 SKU 等没有被全局覆盖。
- 三张补图槽改为客户第 3 页的左、中、右竖版槽位：`(0.448,5.404,1.367,1.969)`、`(2.258,5.404,1.354,1.969)`、`(4.069,5.329,1.313,1.969)` 英寸。图片按原比例 cover 裁剪；缺图继续替换为透明像素，无蓝色矩形、样例图片或说明文字。
- `add_slide(source.slide_layout)` 会先物化 11 个布局占位符，随后完整克隆商品页会造成重复对象。克隆逻辑现先删除这些新实例，再复制标准商品页；主题、母版、背景、布局关系和静态媒体未变。

## 验证与样例

- 五份 Git 忽略的私有虚构样例已重新生成至 `.codex-assets/official-ppt/samples/v5/`：complete、partial、no-image、boundary-safe、five-single-products。
- 新增独立纯渲染器测试：虚构非空京东大客户价只使值 Run 变红；三张不同虚构补图验证左中右顺序、客户坐标和等比裁剪；四项指定字段验证单倍行距；克隆页验证不重复布局占位符。
- 使用 `python-pptx` 对五份输出做结构复核：每个商品页为 15 个对象、没有布局占位符、恰有 4 个图槽。运行模板继续经 ZIP 校验排除人工样例页及其媒体哈希。
- 当前机器没有 PowerPoint、WPS 或 LibreOffice 可执行文件，不能在此环境生成实际桌面渲染截图；需在配有其中任一渲染器的授权环境中打开上述五份输出作最终视觉复核。

## Migration / API / Permission

无 Alembic Revision；无 API、UI、权限、数据库、业务报价或推荐规则变化。
