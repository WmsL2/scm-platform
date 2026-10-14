# Change Record：模板 2 两页正式原件原位回填重做

日期：2026-10-13
模块：recommendation
状态：CODE IMPLEMENTED / WPS RENDER VERIFIED / CUSTOMER VISUAL ACCEPTANCE PENDING

## 原件版本与旧产物清理

用户明确批准本机两页 PPTX SHA-256 `4C1C4922D63F7932A37E51308A25EA3B426CF4CA7F126DCB43AAF208447F1657` 替代此前指定 SHA。TXT SHA-256 `AFB9154EE68F5DE9907EA85CE33953A64DD4EA124C445523BCB1BF54F2014201`。原件两页，封面 1 个形状、商品页 11 个形状，结构指纹 `4f203800d937e32a423d3d3732fa4bf5b2b5020076b915ee82fb0cc13da61198`。

逐个验证路径、大小、SHA 和非 Git 跟踪状态后，删除 1 个错误 v5 运行资产、7 个旧虚构样例、1 个过期审查补丁。原件、历史 v3/v4、模板 1 v5、模板 3--5 及未提交代码不删除、不覆盖；旧原件此前由用户自行更换。

## 原位合同

- 完整保留属性框的原始 Run、两段和首段软换行。七个独立值层复制对应预留 Run 前的原件内容并设置前缀透明，以原字体和原段落属性定位；固定标签不移动，值互不推动。
- 动态价格映射：`prices.market_price` 为冻结 `price_snapshot.market_price`，`prices.agreement_price` 为冻结 `price_snapshot.agreement_price`。有值填入、无值清空值 Run；不读 `jd_price`、活动价、逐件组合价或组合总价。
- 标题、卖点值沿用原 Run 样式；四条卖点沿用 Wingdings 菱形项目符号、缩进、段落位置、1.5 行距及原框几何，不调用 `frame.clear()` 重建。
- 全部固定值槽、单行标题及四条卖点均检查容量，禁止截断、缩字或新增续页。卖点固定四行按字体、1.5 行距、1.2 安全行高检查可用高度。
- 主图和三附图保留原位置；图片等比 contain，不重复，缺图不把后续图片提前。三个补图仅有纯渲染器虚构测试入口，不新增业务数据来源。
- 组合价格/属性展示合同未确定，受控拒绝。默认模板版本仍为 v3。
- 构建阶段验证 PPTX/TXT SHA、两页几何/类型指纹与原标签/项目符号；先写临时文件验证后原子发布。运行资产标记绑定批准源 SHA，并校验所有槽位/Token、几何及 Run/媒体/主题/母版/布局摘要，损坏文件受控 AppError。

## 验证

- 完全虚构的公共 CI 两页结构夹具，30 项专项测试通过，覆盖固定框 XML、静态几何、Run 样式、价格串位/空值、项目符号、图片顺序/缺图/比例、连续五件、超长字段、错配/损坏资产及原子失败。
- 本次 8 份私有虚构 PPTX 均显式调用 `JD_FESTIVE_RED` + `5`，走真实运行资产解析；JSON 留存加载路径、SHA、封面与固定框不变的断言及超限拒绝记录。
- `pytest --collect-only -q`：428 collected；`pytest -q`：428 passed（64.47s），包含 Recommendation、模板 1 v5 及 v3/v4 回归。
- `ruff check .`：All checks passed；`mypy app`：Success（138 source files）。
- `pytest tests/recommendation -q`：182 passed（33.92s）。
- 隔离 Git 索引中 `git apply --check --cached` 与应用后的 `git diff --cached --check` 通过；工作区 `git diff --check` 通过。补丁不包含任何私有 PPTX、图片、运行资产或此前 v4 修改。
- 实际发现 D 盘 WPS（COM 版本 12.0），已只读导出全部 8 份样例 23 页及原件两页，逐页查看 15 个商品页；8 个封面逐像素等同原件，每个商品页八个固定标签/提示区域裁片逐像素等同原件。金额/SKU/物流、四菱形卖点、四图顺序/等比和缺图、长字段边界均已复核。
- 系统字体注册中未找到指定京东字体，可能发生字体回退；指定字体下的字形/容量边界、真实商品主体图以及客户最终视觉验收仍待完成，不以结构测试或当前 WPS 渲染替代。

Alembic Revision：无。API、UI、Permission、数据库、选品和报价规则变化：无。未启动服务；运行模板构建及实际 PPTX 生成入口已本机验证。未 commit、push 或创建 PR。
