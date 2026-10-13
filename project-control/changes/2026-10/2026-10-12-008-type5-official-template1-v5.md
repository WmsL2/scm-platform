# Change Record：Type-5 正式模板 1 v5 试点

日期：2026-10-12
模块：recommendation
状态：IMPLEMENTED / PRIVATE ACCEPTANCE PENDING

## 范围

仅接入正式模板 1，模板 code 为 `JD_DETAIL_RED`、版本为 `5`。`SYSTEM_DEFAULT`、线上当前 v3、私有 v4、模板 2--5、选品、报价、API、权限和数据库均未修改。

## 私有资产与运行时合同

- `scripts/build_private_official_ppt_template_v5.py` 仅从 Git 忽略的 `.codex-assets/official-ppt/originals/模版1.pptx` 派生运行模板至 `.codex-assets/official-ppt/runtime/JD_DETAIL_RED_OFFICIAL_CLEAN_v5.pptx`。
- 运行模板只保留固定封面和标准商品页；人工样例第 3 页被删除。ZIP 校验拒绝第 3 页、其关系或样例媒体哈希残留。
- 动态字段变为稳定命名槽位及精确 Token。运行期只写 Token Run，不做全文模糊替换；未标记固定文案、背景、母版、LOGO、装饰及封面均不改动。
- v5 仅在显式 `PPT_TEMPLATE_ASSET_DIR` 指向授权私有目录时可解析；不存在时明确返回资产不可用，不会回退公开 v3 资产。模板目录默认仍展示/使用 v3。

## 冻结字段与缺失策略

| 展示字段 | 冻结来源 | 缺失行为 |
| --- | --- | --- |
| 商品名称、品牌、SKU、规格、包装、卖点、物流 | `single_products[].product` | 仅清空 Token 值，固定标签保留 |
| 市场参考价、折扣率 | `single_products[].prices.market_price`、`discount_rate` | 空则留空；折扣率仅格式化已冻结的 0--1 比例，不重新计算 |
| 备货时间 | `single_products[].manual.fulfillment_cycle` | 空则留空 |
| 京东大客户价、起订量 | 无可靠冻结字段 | 固定标签保留，动态值始终空；不映射京东价、协议价或活动价 |
| 主图 | 冻结商品 `id` 对应受控 `product_images` | 空图槽为透明像素；不出现蓝色占位或文案 |
| 三张补图 | 当前无受控补图集合 | 始终透明，不复制主图 |

`discount_rate` 已确认进入 `PptCatalogService` 的冻结 `price_snapshot`，因此不是导出时对实时商品或价格的重新查询。

## 内容与图片安全

- 文本按模板要求保留：标题为京东朗正体玲珑 14pt 白色粗体；市场价为 14pt 黑色；京东大客户价为 14pt 红色；规格/包装/物流/卖点为微软雅黑 12pt。
- 固定高度区域有保守容量校验。超过已确认安全容量时返回 `PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED`，不缩小字号、不截断，也不输出部分不可见文字。本轮没有已确认的 v5 续页版式。
- 图片原槽尺寸和图层位置不变，按 cover 裁剪填充，横竖图均保持比例。
- v5 当前明确仅支持单品页；收到组合输入返回 `PPT_TEMPLATE_COMBINATION_UNSUPPORTED`，防止在未确认组合版式下生成错误正式页。

## 验证

- 虚构私有样例：完整单品（一张横图）、部分字段为空（一张竖图）、无图、连续五个单品、容量边界单品。
- 自动化：`tests/recommendation` 121 passed；Ruff 通过；Mypy 通过；`git diff --check` 待本轮最终检查。
- 环境没有 PowerPoint、WPS 或 LibreOffice CLI，无法声明桌面渲染视觉验收通过。待人工重点检查：正式字体实际回退、红白标题栏的长文本视觉高度、图片主体裁剪、固定封面及第 2 页静态元素。

## Migration / API

无 Alembic Revision、API、UI、权限或数据库变化。
