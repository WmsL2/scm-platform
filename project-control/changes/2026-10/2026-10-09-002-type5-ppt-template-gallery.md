# Change Record：类型 5 PPT 内置模板选择

日期：2026-10-09
分支：`codex/feat/type5-ppt-template-gallery`

## 变更

- 增加固定五项模板目录：`SYSTEM_DEFAULT`、`JD_DETAIL_RED`、`JD_FESTIVE_RED`、`CATALOG_MINIMAL`、`UNION_QUOTE_WHITE`。
- 类型 5 生成任务冻结模板编号和版本；未传编号的旧调用继续使用系统默认版。
- 工作台增加单选模板卡片，并在生成历史显示所用模板。
- 渲染继续输出原生可编辑 PPTX；套装会替代其组成商品的独立页。
- 补充五张公开可分发的虚构数据 SVG 预览，不携带原始业务 PPT 的客户、商品、报价、链接、图片或品牌标识。
- 套装的 2–4 张图片按每套模板的专属图片区排列；节庆模板改用浅色信息面板；极简模板标题和正文分区。长规格和卖点会以“详情续页”保留，不裁掉价格或名称。
- 活动价仅在人工确认值存在时标记为“人工确认活动价”；否则明确显示“当前协议价”。任务执行时复核冻结的模板版本。

## 安全与部署

- 原始客户样例只用于本地受控目录 `.codex-assets/ppt-template-sources/` 的结构审查，未加入版本控制或运行时复制链路。
- 渲染器依据审查后的固定版式新建页面，绝不复制样例客户名称、商品、价格、图片或链接。
- 当前环境没有可自动化的 Office/WPS/LibreOffice 渲染器；以 `python-pptx` 重新打开和 ZIP 结构验证替代桌面视觉截图。前端预览为使用虚构数据的可分发 SVG。

## 数据库 / 接口

- Revision：`20261009_0051`，`scm_ppt_generation_task` 新增 `template_code`、`template_version`，已有记录默认为 `SYSTEM_DEFAULT` / `1`。
- 新增 `GET /api/v1/ppt-solution-projects/templates`；生成请求可选 `template_code`，继续接受 `use_default_template`。
- 权限不变：目录使用 `recommendation:detail`，生成与下载沿用 `recommendation:export`。
