# Change Record：Type-5 模板 3 CATALOG_MINIMAL v5

日期：2026-10-15
模块：recommendation
状态：IMPLEMENTED / PUBLIC ASSET VERIFIED / BUSINESS E2E PENDING

## 范围

实现模板 3 `CATALOG_MINIMAL` 的正式 v5：独立渲染模块、版本化 Manifest/注册/分发、审核后 CLEAN 运行资产构建与公共迁入、虚构测试和 WPS 文件级验收。模板 1、2 客户渲染逻辑、模板 4/5、v3/v4、DeepSeek、选品、报价、真实数据、数据库、API、UI 和权限均未改动。

## 原件与资产合同

- 只读原件为两页、13.333 × 7.5 英寸的 `模版3.pptx`；SHA-256 为 `2d9da8beee187e6a0f457a07c0447945f80605fedb15c5a413b38e2639062321`，结构指纹为 `747997d01c664eb24c38b2aec0fcbed494869fda4fa6b36fd97a9aca67cd89dc`。配套 TXT SHA-256 为 `561c7b08a569e343947c1ea61eedfc21ef7e72c5b06f20197677e5820c1f7d24`。
- 第 1 页为空白商品页：左侧一个图片说明区、右侧一个 21 段文字框及两张右侧装饰图；第 2 页为含样例商品、样例分类、样例主图和京东链接的演示页。
- 私有运行资产只保留第 1 页，将左侧说明区替换为一个透明主图槽，删除第 2 页、备注关系、样例文本、样例链接和样例商品媒体。构建先写同卷临时候选，完成结构、Token、几何和媒体白名单校验后原子替换。
- 此前正式私有运行资产从主仓库只读原件构建并原子发布到 `C:\Users\Administrator\Desktop\code\zhongcheng-scm-platform-template3-v5\.codex-assets\official-ppt\runtime\CATALOG_MINIMAL_OFFICIAL_CLEAN_v5.pptx`；其当时 SHA-256 为 `2dbc0e9284f05bf43281cd607f942cd0ca5600b1498c89333ced29982691e1e2`，大小 `102,289` bytes。原件 2 页，运行资产 1 页，四个命名对象为主图槽、动态文字槽及两张静态装饰；原件 SHA、TXT SHA、结构指纹、Token/几何合同和媒体白名单均通过。该旧 SHA 后因公共元数据复审废止，当前发布值见下一条。
- 2026-10-15 客户明确授权审核后的 CLEAN v5 资产及其右侧两张静态装饰公开分发。首次迁入文件 SHA-256 为 `2dbc0e9284f05bf43281cd607f942cd0ca5600b1498c89333ced29982691e1e2`，后续独立复审发现其仍携带演示文稿级历史元数据，因此该 SHA 已废止，不能发布。
- P0 元数据修复后，标准化程序从未修改的正式原件重新构建公共资产；最终 `assets/ppt-templates/CATALOG_MINIMAL_OFFICIAL_CLEAN_v5.pptx` SHA-256 为 `953743f5947b7012170eeffa5dbf4a16c710dcbf8dd26c7b7f63eb263931c735`，大小 `64,591` bytes。包文件由 110 个降至 43 个，共移除 67 个文件部件：62 个 Office 标签部件、2 个 notes master 文件、1 个批注作者文件、1 个自定义属性文件及 1 个随 notes master 失去引用的主题文件。最终包保留 1 页、3 个白名单 PNG 媒体、2 个必要主题及客户授权的两张静态装饰。

## 公共资产元数据安全合同

- 标准化同时删除批注作者、comments、notes slides/masters、Office 标签、`docProps/custom.xml`、`customXml`、OLE/ActiveX/embedded package、宏及其关系；从对应源 XML 删除关系 ID 引用，并清理空的 notes/tag 容器，不能产生悬空关系。
- `docProps/core.xml` 仅保留资产版本标记与结构合同摘要，不保留作者、最后编辑者、创建/修改时间、revision 或其他个人身份/编辑历史。
- `docProps/app.xml` 只保留非身份属性，并按最终包重写为 `Slides=1`、`Notes=0`、`HiddenSlides=0`、`MMClips=3`；旧 HeadingPairs/TitlesOfParts 和编辑统计被移除。
- 运行资产校验扫描整个 OOXML 包，拒绝禁止部件、邮箱形式身份内容、外部关系、嵌入对象、隐藏页、缺失关系目标及 XML 对不存在 relationship ID 的引用。媒体白名单、Manifest、几何、Token、Run 样式和结构摘要仍需同时通过。
- 跨平台复审修正了 OOXML 关系源的路径解析：ZIP 内部名称现统一由 `PurePosixPath`/`posixpath` 处理，不再把 `/` 替换为 Windows `\`。根关系、presentation、slide、slideLayout、slideMaster 及其相对目标共用同一 POSIX 解析规则，清理器和校验器因此在 Windows/Linux 上得到相同的包部件名称。正式公共资产的每条内部关系均重新验证为非外部且目标存在，被清理部件的关系和源 XML 引用仍同步移除。

## 样式优先级确认

原件与 TXT 的颜色/粗体存在冲突。2026-10-15 经客户明确确认，仅冲突字段以 TXT 为准：

- 型号和零售价值使用 `#9D908B`；
- 商品名称、规格参数和产品特点使用黑色 `#000000`；
- 京东链接标签和值全部为黑色、粗体，保留 Run 的真实 http/https 超链接目标；
- 其他字体、字号、1.5 倍行距、段落位置、文本边距、静态装饰和版式沿用 PPT 原件。为防 WPS 将链接强制显示为主题蓝色，CLEAN 运行资产只把 hyperlink/followed-hyperlink 主题色设为黑色；页面不存在其他超链接。

## 字段与版式合同

| 客户字段 | 冻结输入 | 空值行为 |
| --- | --- | --- |
| 型号 | `product.model` | 留空 |
| 商品名称 | `product.product_name` | 留空 |
| 规格参数 | `product.product_specification` | 保留固定标签，值留空 |
| 零售价 | `prices.jd_price` | 保留标签，不显示金额单位 |
| 团购价 | `prices.agreement_price` | 保留标签，不显示金额单位 |
| 产品特点 | `product.selling_points` | 保留固定标签，值留空 |
| 京东链接 | `product.jd_same_product_url` | 保留标签，无超链接关系 |
| 商品主图 | `product.id` 对应已加载图片 | 透明留空，不复用其他图片 |

2026-10-15 用户正式确认：零售价只映射当前任务冻结 `prices.jd_price`，团购价只映射当前任务冻结 `prices.agreement_price`。此前迁移审计中“模板 3 价格含义待确认”的事项已解决；原 `prices.market_price` 零售价映射已纠正，且绝不以 `market_price` 兜底、替代或重算价格。有效 `0` 显示为 `0.00`，空值只清空动态值并保留客户固定标签。

链接只接受完整 http/https 地址，非法协议、内部换行、制表符、空格及控制字符均受控返回 `PPT_TEMPLATE_LINK_INVALID`；链接在校验前不 trim 或规范化，因此不会将非法原值隐式改写为可接受地址。主图按 `contain` 居中等比展示，不裁切、不拉伸；原件只有一个商品图槽。模板当前仅支持单品，组合输入返回 `PPT_TEMPLATE_COMBINATION_UNSUPPORTED`。

型号、名称、规格、卖点及链接按原框安全宽度、Run 字号和 1.5 倍行距估算视觉行。连续 ASCII 型号及 URL 会在进入右侧装饰前完整分行；链接容量与最终逐段 Run 写入共用 `_wrapped_chunks`，首行先扣除固定“京东链接：”的实际估算宽度，后续行使用完整安全宽度。每行均保留原始完整超链接目标，拼接显示值不丢字、不改序。链接为空不创建关系。规格和卖点共享原件预留空白并按累计视觉行占用空间；渲染后另按实际生成的高/低字号行数校验可见文字底边，而非只检查文本框几何。页面确实无法容纳时返回带商品标识和 pt 诊断的 `PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED`，不缩字、不截断、不增加非客户版式续页。

## 验证

- 模板 3 v5 专项：`43 passed`。除身份/批注/标签/自定义属性清理、禁止部件拒绝、最终公共资产 SHA、默认目录 Resolver/`PptRenderer` 分发合同外，新增根关系、presentation、slide、slideLayout、slideMaster 关系源和相对目标的跨平台 POSIX 解析测试；测试直接对仓库公共资产执行 `validate_catalog_minimal_v5_runtime()`，逐条确认无外部或悬空关系。
- 模板 1/2/3 v5 联合专项：`159 passed`。
- Recommendation 全量：`283 passed, 9 failed`。9 项均为需要 MySQL 的既有 HTTP/Service 集成用例，因本机没有获准的隔离测试库凭据而连接 `scm_dev@localhost` 被拒绝（MySQL 1045）；未迁移或写入真实数据库，不属于本次渲染代码失败。全量回归显式关闭仅供本地工作台展示的默认 v5 开关，以保持历史图库基线断言。
- `ruff check .`：passed。
- `mypy app`：Success（146 source files）。
- `git diff HEAD --check`：passed。
- Linux/WSL 独立运行：本机 WSL 未安装发行版，Docker Desktop Linux engine 也未运行，因此未能获得独立 Linux 进程。测试通过固定 POSIX 输入/期望值覆盖该分支，并在 Windows 上对 43 个正式公共资产部件执行完整运行时及逐关系校验；仍建议 CI 的 Linux runner 再执行同一专项测试。
- 公共 PPTX 未重新构建或修改，SHA-256 保持 `953743f5947b7012170eeffa5dbf4a16c710dcbf8dd26c7b7f63eb263931c735`。
- 私有样例位于 `.codex-assets/official-ppt/samples/v5/catalog-minimal/`：价格映射、零值/缺失值、缺图、横图、竖图、方图、极端宽图、长型号/规格/卖点/连续 ASCII URL 的接近底边安全边界、首行标签宽度边界及连续五商品。
- 实际加载验证：Worktree `.env`（Git 忽略）现将 `PPT_TEMPLATE_ASSET_DIR` 解析为 `C:\Users\Administrator\Desktop\code\zhongcheng-scm-platform-template3-v5\assets\ppt-templates`，并保留 `PPT_V5_PREVIEW_ENABLED=true`、`PPT_LOCAL_V5_DEFAULT_ENABLED=true`。Manifest 解析文件名为 `CATALOG_MINIMAL_OFFICIAL_CLEAN_v5.pptx`，真实 `PptRenderer.render(..., template_code="CATALOG_MINIMAL", template_version="5")` 从公共目录解析上述 SHA 文件并进入 `render_catalog_minimal_v5()`；新增回归也验证完全不设置资产目录时的新隔离检出会从仓库默认公共目录解析同一 SHA。显式 v3 仍解析 v3；模板 3 v4 文件在原有资产目录中不存在，显式 v4 受控报资产不可用而不回退。
- WPS 12.0 已打开元数据清理后的新公共资产输出。单一 COM 会话连续打开多份文件时出现过 RPC 服务不可用，因此改为每份关键样例使用独立 WPS 会话；`wps-metadata-clean-keycases-20261015-153219933` 中正常单品、零值/缺失价格、缺图、长文本/URL、首行 URL 边界及连续五商品均成功导出。PNG 复核确认主图等比、价格、链接换行、两张静态装饰、字体及页面边界与修复前一致，无重叠或越界。

## 影响与剩余事项

- Alembic Revision：无。
- API / UI / Permission：无变化。
- 公开资产：新增 Git 跟踪的 `assets/ppt-templates/CATALOG_MINIMAL_OFFICIAL_CLEAN_v5.pptx`。客户原件、私有副本、样例和 PNG 均未加入 Git；客户已授权公开的范围仅限该 CLEAN 资产内的一页商品版式及两张静态装饰。
- 剩余发布条件：真实工作台与客户最终视觉确认。装饰媒体的公开分发授权已由本次用户指令确认，不再作为本资产的发布阻塞项。
- 真实业务验收：DeepSeek 当前不可用，未调用 DeepSeek，真实选品端到端验收延期。
- 本机启动验证：未发现正在运行的本地后端，因此不存在误用主仓库旧服务的情况；未启动需要 MySQL 的工作台服务。正式资产已通过真实业务渲染入口的文件级验证，但尚不等同于真实工作台业务验收。
