# ADR-0052：类型 5 私有 PPTX 真模板资产

状态：ACCEPTED
日期：2026-10-09

## 决策

- `JD_DETAIL_RED`、`JD_FESTIVE_RED`、`CATALOG_MINIMAL` 和 `UNION_QUOTE_WHITE` 的生成改为读取受控 PPTX 资产中的封面和标准商品页；`SYSTEM_DEFAULT` 继续由既有代码渲染。
- 每套资产使用经过人工结构审查的“幻灯片索引 + 形状索引”槽位清单替换商品字段和媒体，禁止通过客户样例文字做模糊匹配。
- 运行时保留主题、母版、布局、背景和静态关系；新增页会连同关系复制标准商品页。源模板中非授权的商品图片、业务文字、链接、备注和未选页面会被移除或替换。
- 资产路径由 `PPT_TEMPLATE_ASSET_DIR` 指向部署侧的授权私有目录；仅开发/测试环境可回退到 Git 忽略的 `.codex-assets/ppt-template-sources/`。资产不存在时返回 `PPT_TEMPLATE_ASSET_UNAVAILABLE`，不退回低保真重绘。

## 后果

- 原始客户 PPTX 和其媒体始终不进入 Git、镜像或公开构建产物。
- 模板版本仍由现有任务冻结字段校验；本决策不修改数据库、API 权限或 DeepSeek/候选选择流程。
- 未取得明确授权的品牌标识或装饰图片不能作为新公共模板资产分发；部署者需对私有资产的授权与脱敏负责。
