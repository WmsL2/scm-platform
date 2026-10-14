# Change 2026-10-14-009：模板 2 v5 属性原位回填与渲染架构审查

## 范围

- 仅修改 `JD_FESTIVE_RED` v5 的商品属性写入方式及其虚构验收脚本/测试。
- 不修改 `JD_DETAIL_RED` v5、v3/v4、API、数据库、权限、价格计算或公共 PPTX 资产。
- 公共运行资产仍为 `assets/ppt-templates/JD_FESTIVE_RED_OFFICIAL_CLEAN_v5.pptx`，SHA-256 为
  `F0814AF47B80B281E3407C4373CA88F03E3CDFF7409DC30473E71DA7070D12B7`。

## 缺陷与修复

正式商品页的市场参考价、京东大客户价、折扣率、SKU、货期、发货物流/快递和质保原本都在
`SCM_FIELD_REFERENCE` 同一原始文本框的两个段落内。标准化过程又为七个值创建了
`SCM_VALUE_*` 浮动文本框，渲染时依赖估算的绝对坐标摆放这些浮层。WPS 的实际换行、字体度量与
估算坐标不一致后，浮层会覆盖固定标签并彼此重叠。

渲染输出现在直接替换 `SCM_FIELD_REFERENCE` 中七个客户预留的空白 Run。固定标签 Run、段落
属性、字体、字号、颜色、粗细、1.5 倍行距和文本框边距均不重建。中间字段仅在值末尾保留一个
字段间隔；标签冒号和值之间没有额外空格、换行或制表符。缺值时动态 Run 为空，业务快照中的
数值零仍由既有格式化函数显示。克隆出的商品页会移除旧 `SCM_VALUE_*` 渲染浮层，公共运行
PPTX 本身不变。

长属性按原始属性框的完整有效宽度自然换行；属性框按三条原始视觉行之外的新增行扩展，并沿用
模板 2 既有的下方卖点、图片标题和图片槽联动。真实页面空间不足时仍返回受控容量错误。此前已
验收的第五、第六条卖点 XML 复制和卖点区域联动未改变。

## 本地渲染架构审查

调用链：

`POST generations` → `PptSolutionService.create_generation()` 冻结 code/version →
`execute_generation()` 组装冻结快照 → `PptRenderer.render()` →
`get_ppt_template(code, version)` / `get_pptx_manifest(code, version)` → 版本分发 →
模板渲染器字段映射、填充与布局 → `python-pptx` 保存 → Storage 保存并把任务置为 `SUCCEEDED`。

| 模板 code/version | 入口 | 实际渲染文件 | 字段填写 | 布局/容量 | 共用情况 |
|---|---|---|---|---|---|
| `SYSTEM_DEFAULT` v1 | `PptRenderer.render` | `ppt_renderer.py` | `_product_template_entries`、`_populate_template_slide` | `_paginate_details`、`_fit_slot_text` | 系统默认独立路径 |
| 四套业务模板 v3 | `_render_business_template` fallback | `ppt_renderer.py` | `_populate_template_slide` | `_fit_slot_text`、通用图片网格 | 四套共用通用槽位渲染器，由 manifest 区分槽位 |
| 四套业务模板 v4 | `render_v4` | `ppt_renderer_v4.py` | `_fields`、`_replace_tokenized_runs`、`_populate_page` | v4 公共分页/容量函数，内部按 code 分支 | 四套共用一个 v4 模块；JD 详版和节庆版有模板条件分支 |
| `JD_DETAIL_RED` v5 | `render_jd_detail_red_v5` | `ppt_official_template_v5.py` | 模板 1 专属 Token/Run 填充 | `_layout_dynamic_text` 及可见文字边界 | 完全独立于模板 2 |
| `JD_FESTIVE_RED` v5 | `render_jd_festive_red_v5` | `ppt_official_template_festive_v5.py` | `_item_values`、`_fill_reference_values`、`_append_selling_points` | 模板 2 `_layout_dynamic_text` | 完全独立于模板 1 |
| 模板 3、4 v5；模板 5 | 无入口 | 无 | 无 | 无 | 未实现、未注册，不得视为可用 |

结论：当前并非所有版本都“一模板一文件”。v3 四套共用 `ppt_renderer.py` 的通用槽位逻辑，v4
四套共用 `ppt_renderer_v4.py` 并含 code 条件分支；两套已实现 v5 各自拥有独立渲染模块、字段
映射和布局算法。修改模板 1 v5 不会通过直接函数调用影响模板 2 v5，但二者仍共享注册、manifest、
资源解析和 `PptRenderer` 分发入口，这些公共合同的修改必须做跨模板回归。

显式 `(template_code, template_version)` 决定渲染器。v4/v5 都有精确 manifest；缺失版本返回受控
错误。请求省略版本时，生产安全默认仍取 v3；只有 development/local 环境同时开启本地 v5 默认
开关时，模板 1、2 才默认 v5。因此不存在“显式 v5 静默回退 v3”，但调用方省略版本时必须理解
环境默认规则。

继续开发模板 3、4、5 v5 时，建议每套新增独立模块、精确 versioned manifest、运行资产结构合同、
字段映射、容量/布局和专项测试；只抽取无客户几何语义的加载保存、关系克隆、图片 contain/cover、
Run 样式复制和通用度量辅助。不要把模板特有标签、段落索引、坐标、行距或联动规则放进跨模板
公共分支。

## 验证

- 模板 2 专项：`43 passed`。
- 模板 1 专项回归：`72 passed`。
- Recommendation 全量：`236 passed`。
- Mypy：`Success: no issues found in 139 source files`。
- Ruff（后端应用、Recommendation 测试、脚本）：通过。
- 仓库根目录 `ruff check .` 会扫描本地未跟踪的 `.tools/libreoffice/extracted` 第三方发行文件并报告
  8,672 项第三方问题；未修改这些工具文件。
- `git diff --check`：通过。
- WPS `KWPP.Application` 12.0 实际打开并导出 complete、空字段、缺图、五商品、四图、价格映射、
  六卖点等虚构样例。顶部七个属性均与固定标签连续显示，无浮层遮挡；六条卖点完整，图片和装饰
  联动保持不变。

## 数据库与接口

- Alembic Revision：无。
- API / UI / Permission：无变化。
- 本机启动验证：未启动前后端；按任务限制仅执行纯渲染器和 WPS 文件级验证。

## 后续

- WPS 虚构样例已完成技术视觉复核，仍等待用户用实际商品在现有本地工作台最终验收。
- 模板 3、4、5 v5 尚未实现，应按独立模板合同逐套开发和审查。
