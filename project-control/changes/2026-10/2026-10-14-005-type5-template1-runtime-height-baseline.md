# Type-5 模板 1 v5 使用运行 PPT 实际高度作为排版基线

日期：2026-10-14  
模块：Recommendation / Type-5 PPT  
状态：IMPLEMENTED / WPS RENDER VERIFIED / CUSTOMER ACCEPTANCE PENDING

## 根因

运行资产中的动态文本框经 WPS 合法调整后，`ppt_official_template_v5.py` 仍用代码常量逐项比较 `left/top/width/height`，因此任何高度变化都会被判为“文本槽位几何合同不匹配”。渲染阶段还会固定把左右价格框各缩短 21pt，并把后续右栏对象上移 21pt，实际覆盖运行 PPTX 自身的纵向设置。

## 修复

- 运行合同只保留审核过的水平列 `left/width`；`top/height` 从当前私有运行 PPTX 读取，不再与 Python 高度常量比较。
- 所有必需文本槽仍必须存在且唯一、必须是文本形状、必须含唯一正确 Token；图片槽仍必须存在且唯一并为图片类型。
- 每个文本槽继续校验正尺寸、有效内边距和完整页面边界；页数、商品页 15 个形状及卖点固定标题合同不变。
- 移除运行期固定压缩价格区 21pt 的逻辑。标题、价格区、品牌、规格、包装、物流和卖点均以运行资产当前 `top/height` 为基准。
- 动态高度继续比较填充前 Token 文本高度与填充后真实文本高度；只有新增自动换行产生增量，后续关联形状按资产原始坐标累计移动一次。
- 标准化构建器、客户原件、图片、字段映射、字体字号、价格纯数值、协议价来源和排版诊断模式均未修改。

## 私有资产核验

- `.env` 实际解析目录：`.codex-assets/local-v5-runtime/ppt-templates/`。
- 实际运行资产：`JD_DETAIL_RED_OFFICIAL_CLEAN_v5.pptx`。
- SHA-256：`D2E3CFFE8D22601A5017B64E0C3A878842EE241718A3EFE8FCD3EAE732F92C2D`。
- 私有只读备份：`JD_DETAIL_RED_OFFICIAL_CLEAN_v5.backup-20261014-D2E3CFFE8D22.pptx`，哈希与源文件一致。
- 未重建或覆盖运行资产；未修改 `originals/模版1.pptx`。

## WPS 验证

- 正式短字段虚构样例保留运行资产实际高度：规格 24.65pt、包装 23.55pt、物流 21.70pt、标题 24.15pt、品牌 29.45pt、参考区 121.55pt、价格区 130.75pt。
- 规格、包装、物流均为两行时，输出高度分别为 36.50pt、36.50pt、36.10pt；包装、物流和卖点按前序增长累计移动，卖点底部 522.31pt，未超出 540pt 页面。
- 两份虚构 PPTX 均可重新打开，并由 WPS 12.0 导出两页 PNG；人工复核未见属性互相重叠。
- 私有样例位于 Git 忽略目录 `.codex-assets/official-ppt/samples/v5/jd-detail-red-runtime-height-baseline/`。

## 验证

- `pytest tests/recommendation/test_official_ppt_template_v5.py -q`：66 passed。
- `pytest tests/recommendation -q`：213 passed、5 failed；5 项均为本地默认模板 1/2 已切至 v5 后，旧测试仍假定所有内置模板默认为 v3、支持组合及旧“协议价：¥”文案，与本轮高度合同无关。
- `ruff check .`：通过。
- `mypy app`：139 source files 通过。
- `git diff --check`：通过。
- Alembic Revision：无。
- API / UI / Permission：无变化。
- 模板 2--5、历史 v3/v4、数据库、价格业务规则和图片逻辑：无变化。
- 本机服务启动：未执行；按任务要求不启动前后端或创建真实任务。
