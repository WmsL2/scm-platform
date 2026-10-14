# Handoff：JD_FESTIVE_RED v5 两页正式原件原位回填

状态：CODE IMPLEMENTED / WPS RENDER VERIFIED / CUSTOMER VISUAL ACCEPTANCE PENDING

## 权威文件

- 私有 `originals/模版2.pptx` 已由用户确认取代此前 SHA；两页，商品页 11 个原始形状，PPTX SHA-256 `4C1C4922D63F7932A37E51308A25EA3B426CF4CA7F126DCB43AAF208447F1657`。
- 同目录 `模版2.txt` SHA-256 `AFB9154EE68F5DE9907EA85CE33953A64DD4EA124C445523BCB1BF54F2014201`。
- 旧四页原件由用户自行删除；本次已删除 1 个旧 v5 运行资产、7 个旧样例和 1 个旧审查补丁。历史 v2/v3/v4、其他模板、未提交代码均保留。

## 实现合同

- 不再重建属性框。固定属性框 XML、原始 Run、空格、软换行、字体与静态提示完整保留。七个透明独立值层复制原件隐藏前缀 Run，Office 使用原始字形宽度/行高定位，值不推动任何标签。
- 运行模板 19 个形状是原有 11 个形状（蓝色附图说明改为透明图片槽）、7 个独立值层及 1 个主图图片层；没有重复布局占位符。
- 市场参考价只用冻结 `price_snapshot.market_price`；京东大客户价只用 `price_snapshot.agreement_price`，服务现有 renderer payload 将其命名为 `prices`。不使用 `jd_price` 或人工活动价。
- 四条卖点沿用原段落、Wingdings 菱形、缩进、行距与 Run 样式；超条数/换行容量拒绝。商品名称也保持原 Run，不缩字。
- 四图按主图、图片 1、图片 2、图片 3 进入原位置，等比完整展示；缺图保持透明，不移位、不复制。补图 ID 仅用于纯渲染器虚构测试，业务没有新增来源。
- 组合价格/属性展示合同仍未批准，返回 `PPT_TEMPLATE_COMBINATION_UNSUPPORTED`，不混用逐件价格和总价。
- 原子构建校验原件/TXT SHA、结构指纹、静态媒体；运行期校验版本、槽位/Token 唯一性、几何及完整 Run/静态媒体/主题/母版/布局摘要。默认仍为 v3。

## 验收材料及待办

- `.codex-assets/official-ppt/samples/v5/jd-festive-red-two-page/` 包含完整、空字段、无图、四图、缺中间图、边界、连续五品、价格映射共 8 份虚构 PPTX，以及记录实际版本/运行资产路径和 SHA 的 JSON。
- 可通过 `scripts/build_private_official_ppt_template_v5.py --template-code JD_FESTIVE_RED` 和样例生成脚本重建。验收脚本走真实私有资产解析器及 v5 分支。
- 本机发现 WPS `D:\ruanjian\WPS Office\12.1.0.28505\office6\wpp.exe`，COM 版本 12.0。经只读导出 8 份样例 23 页及原件两页，已逐页查看 15 个商品页。8 个封面逐像素等同原件；所有商品页八个固定标签/提示区域裁片逐像素等同原件，金额、SKU、物流未推移标签，卖点/四图/缺图/边界排版检查通过。
- WPS 渲染 PNG 与导出清单保存在样例目录，复现脚本 `scripts/render_private_jd_festive_red_v5_wps.ps1`。此发现替代此前“本机无渲染器”的初始判断；不关闭用户已打开的原件，也不保存修改任何输入 PPTX。
- 系统字体注册未找到京东朗正体，因此可能使用 WPS 字体回退；还需安装指定字体的 Office/WPS 最终字形及容量边界验收。容量估算不等同跨字体/跨渲染器的严格排版证明，客户最终视觉验收未完成。
- 当前图片为不同颜色/宽高比的虚构测试板，仅验证顺序与比例；商品主体摄影图的视觉验收仍待完成。
- 未提供问题截图对应的任务 ID，因此不能判定历史生成记录当时选用的版本。代码审计已确认任务保存 code/version、renderer 使用冻结 version、单品快照价格来源正确；本次样例明确使用 `JD_FESTIVE_RED` + `5`。
- 通过代码与视觉审查后再决定部署；不要开始模板 3--5。无数据库、API、UI、权限或报价/选品规则变化，不 commit/push/PR。
