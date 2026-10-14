# Change Record：类型 5 JD_DETAIL_RED v4 组合高保真输出

日期：2026-10-12
模块：recommendation
状态：IMPLEMENTED / 等待桌面视觉验收

## 变更

- 私有 `JD_DETAIL_RED` v4 新增 `packages` 渲染，组合页不再因只读取 `single_products` 而只输出封面。
- 组合固定接受 2--4 个不同冻结商品；按冻结顺序将各商品图片写入既有四个图片槽，剩余槽使用透明图，不复制某个商品来填满所有槽位。
- 套装组成不再使用可分页、会分割字符串的详情组装逻辑。商品名称、SKU、型号在同一行完整写入，禁止输出“套装组成（续）”。
- `JD_DETAIL_RED` v4 runtime manifest 改为只解析私有最终候选 `JD_DETAIL_RED_CLEAN_v4-text-fix.pptx`；虚构单品及 2/3/4 件组合均由该文件实际渲染。
- 私有文本修复脚本将商品详情/组合共用的标题保留原始段落样式，并用受控 `detail_heading` token 在单品显示“产品卖点（介绍详细）”、组合显示“套装组成”。

## 保持不变

- v3 仍为公开默认版本，既有冻结 v3 任务不升级。
- 不修改商品推荐、选品、价格档、组合生成、API、权限、数据库或其他三套模板。
- 原始客户 PPT、客户图片及未获分发授权的静态媒体继续只存在于 Git 忽略的私有目录。

## 验证

- `tests/recommendation/test_ppt_renderer.py`：18 passed，覆盖单品及 2/3/4 件组合图片去重、完整 SKU/型号/名称和最终 text-fix 合同。
- Ruff 与 Mypy 通过；`git diff --check` 通过。
- 已在私有 `.codex-assets/ppt-v4-review/` 生成四份完全虚构的 PPTX。

## 待验收

- 当前环境没有 PowerPoint、WPS 或 LibreOffice CLI；需在桌面渲染器中对最终候选逐页截图，并与授权参考封面和商品页比对字体回退、文本溢出、静态媒体、母版、背景及图层顺序。
