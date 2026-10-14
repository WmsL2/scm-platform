# Type-5 模板 1 v5 按可见文字判断页面边界

日期：2026-10-14  
模块：Recommendation / Type-5 PPT  
状态：IMPLEMENTED / WPS RENDER VERIFIED / CUSTOMER ACCEPTANCE PENDING

## 根因

动态布局此前用右栏形状的 `shape.top + shape.height` 最大值判断页面越界。该值是文本框外框底边，包含最后一行文字下方的 `margin_bottom`，也间接包含高度估算使用的 0.5pt 跨 Office 安全余量。用户诊断中的 540.6pt 是外框底边；它并不表示最后一行字形已经越过 540.0pt 页面。

本地正式运行模板的文本框底部内边距为 3.6pt。按相同段落度量扣除 3.6pt 底部内边距和 0.5pt 计算安全余量后，540.6pt 外框对应的可见文字底边为 536.5pt，仍在页面内。

## 修复

- 动态文本页面下界改为 `top + 估算文本高度 - margin_bottom - 0.5pt 安全余量`。
- 非动态文本、分隔线和其他固定视觉对象仍使用真实形状外框，不放宽真实视觉边界。
- 标题、参考/价格、品牌、规格、包装和物流继续按上下顺序检查可见文字是否进入下一动态属性区域；真实重叠仍返回 `PPT_TEMPLATE_TEXT_CAPACITY_EXCEEDED`。
- 最后一项卖点的可见文字底边超过幻灯片高度时仍受控失败。不会通过删除、截断、缩字或无限容差放行。
- 现有字体、运行模板高度、规格连续段落、自然行高、动态扩展、累计位移、字段映射、价格格式与图片逻辑未改变。

## 诊断输出

- 普通模式始终只生成客户封面和商品页，不生成内部诊断页。
- 显式启用 `PPT_V5_LAYOUT_PREVIEW` 但没有真实可见越界/重叠时，同样不添加诊断页。
- 只有显式诊断模式且确实检测到真实问题时，才追加“排版诊断版（仅用于排版调试）”页面。
- `PptRenderer` 记录本次输出是否实际包含诊断页；PPT 文件名只有在该值为真时才追加“排版诊断版”，不再仅依据环境开关命名。

## 正式私有模板验证

- 虚构规格 5 行、包装 2 行、物流 1 行，输出仍为封面+商品页两页。
- 卖点文本框外框底部为 551.11pt，但卖点实际可见文字底边为 474.41pt；未生成诊断页。
- WPS 12.0 成功打开并导出两页 PNG；人工复核规格、包装、物流、定制说明和卖点之间无重叠。
- 更长虚构规格使可见文字真正超过页面时，正式模式继续返回受控容量错误。
- 私有样例位于 Git 忽略目录 `.codex-assets/official-ppt/samples/v5/jd-detail-red-visible-boundary/`。

## 验证

- `pytest tests/recommendation/test_official_ppt_template_v5.py tests/recommendation/test_ppt_solution_plans.py -q`：79 passed。
- `pytest tests/recommendation -q`：219 passed、5 failed；失败均为本地开发默认 v5 与历史 v3 测试预期冲突（旧测试仍假定业务模板统一为 v3、模板 1 支持组合页、沿用旧“协议价：￥”文案），本轮模板 1 可见边界与干净输出专项无失败。
- `ruff check .`：通过。
- `mypy app`：通过（139 个源文件）。
- `git diff --check`：通过。
- Alembic Revision：无。
- API / UI / Permission：无变化。
- 模板 2--5、历史 v3/v4、数据库、价格、图片和已验收版式：无变化。
- 本机服务启动：未执行；未创建真实任务或修改真实商品。
