# Change Record：Type-5 模板 2 JD_FESTIVE_RED v5

日期：2026-10-13
模块：recommendation
状态：SUPERSEDED / NOT ACCEPTED

此记录为已撤回的四页旧原件实现，不能作为模板 2 验收依据。当前权威两页原件和原位回填重做见 `2026-10-13-006-type5-jd-festive-red-v5-in-place.md`；此处测试数字仅代表历史代码检查，不代表视觉验收通过。

## 范围

仅实现 `JD_FESTIVE_RED` 的私有 v5 运行资产、版本化 manifest、专用渲染器、构建入口和完全虚构的测试/验收样例。模板 1 的既有 v5、所有 v3/v4、模板 3--5、选品、报价、数据库、API、UI 和权限均未改动。

## 私有资产合同

- 原件 `.codex-assets/official-ppt/originals/模版2.pptx` 只读；标准化前校验 4 页、各页形状类型/数量和 SHA-256 结构指纹。
- 运行资产只保留第 1 页固定封面与第 2 页商品页；第 3 页字体说明和第 4 页人工样例被删除。
- 运行资产校验 2 页、商品页 11 个形状、唯一文本/图片槽、Token、几何、固定“方案编号”和市场价提示；错误受控为 `PPT_TEMPLATE_ASSET_STRUCTURE_INVALID`。
- 构建先写入同目录临时 PPTX，完成结构与删除页专属媒体哈希验证后才原子替换正式私有运行资产。

## 渲染合同

- 商品名称为京东朗正体玲珑 20pt 白色粗体；市场价、折扣、SKU 为 14pt 白色 1.5 倍行距；货期、物流、质保为 14pt 白色粗体；卖点内容为 12pt 白色 1.5 倍行距。
- 只读取冻结的商品/价格/人工确认快照。京东大客户价没有可靠独立来源，固定标签保留而动态值为空；右下三个补图槽没有受控来源，保持透明。
- 左侧原有白色主图区支持已确认组合的 1/2/3/4 张不同商品图：单张、上下、上二下一、2×2。图片使用 contain 居中等比布局，不拉伸、不裁切、不以其他图片补位。
- 所有动态区先计算可用宽高、内边距、字号与行距；自动换行超限返回 `PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED`，不会缩字、截断或移动固定元素。

## 验证

- `pytest tests/recommendation/test_official_ppt_template_festive_v5.py -q`：20 passed
- `ruff check .`：passed
- `mypy app`：Success（138 files）
- `pytest --collect-only -q`：418 collected
- `pytest -q`：418 passed
- `git diff --check`、`git apply --check --cached <review patch>`：passed

私有虚构样例位于 `.codex-assets/official-ppt/samples/v5/`，包括完整、缺字段、缺图、边界、连续五件、1--4 件组合网格及横竖主图比例。当前环境没有 PowerPoint、WPS 或 LibreOffice，桌面渲染截图复核仍为审查前待办。
