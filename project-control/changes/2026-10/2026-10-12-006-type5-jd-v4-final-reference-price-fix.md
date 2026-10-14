# Change Record：JD_DETAIL_RED 私有 v4 参考区与价格换行修复

日期：2026-10-12  
模块：recommendation  
状态：IMPLEMENTED / 待桌面渲染复验

## 根因与修复

| 问题 | 根因 | 修复 |
| --- | --- | --- |
| 长 SKU 导致履约与品牌/型号视觉重叠 | `SCM_FIELD_REFERENCE` 宽度仅约 2.53 英寸，使用 14pt 三行文字；旧 SKU 容量未计算静态标签及框内边距，ASCII SKU 仍可能换为第四行 | SKU、履约限制收紧为含标签的一行保守容量，品牌/型号限制同步收紧；任一超出时整段转入固定详情续页，参考与品牌字段不再自动扩高。 |
| 套装总价将 `¥` 与金额拆到两行 | 18pt 金额 Run 中的普通空格被 PowerPoint/LibreOffice 作为断行位置 | 仅在价格 token 的可视输出中将 `¥ ` 替换为不可断行空格 `¥ `；视觉文本保持“¥ 399.00”，Run 继续使用模板的 18pt 红色样式，金额来源和价格语义不变。 |

## 验证

- `pytest tests/recommendation -q`：`113 passed`。
- PPT 渲染专项：`27 passed`；Ruff、Mypy（`ppt_renderer_v4.py`）与 `git diff --check` 通过。
- 已重新生成 Git 忽略的虚构 `boundary`、`combination-2`、`combination-3`、`combination-4`、`multi-combination-5` round2 输出。
- 结构复核：边界集 10 页；含长 SKU/履约/品牌型号的商品页参考框只保留市场价，长字段均位于续页。组合价格 Run 均读取为不可断行的 `¥ 399.00`（及相应总价），并保留 18pt 红色样式。

## 范围

- 仅 JD_DETAIL_RED 私有 v4；v3、其他模板、选品/报价规则、API、权限和数据库未改。
- 无 Alembic Revision；没有提交客户原件、客户图片或私有模板。
- 当前环境没有 PowerPoint、WPS 或 LibreOffice CLI，最终实际桌面渲染仍需在受控桌面执行。
