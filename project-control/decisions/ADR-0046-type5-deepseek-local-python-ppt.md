# ADR-0046：类型 5 使用 DeepSeek 选品与本地 Python 生成 PPT

状态：ACCEPTED
日期：2026-09-30

## 背景

ADR-0041 将类型 5 的语义选品和 PPTX 生成交给 Kimi 及 Hosted Agent。实际 Kimi API 没有可稳定集成的 PPT 文件生成能力，导致正确的 API Key 也无法完成可下载 PPTX 的业务闭环。

## 决策

- 类型 5 的需求理解和受控候选排序统一使用既有 DeepSeek 结构化适配器；类型 4 和类型 5 共用 `DEEPSEEK_*` 配置。
- DeepSeek 只能对后端提供的 Product Master 候选返回结构化结果；候选 ID、人工确认、套装金额、项目状态、审计和文件保存继续由确定性业务代码处理。
- 人工确认完成后，后端以 `python-pptx` 在本机生成原生可编辑 PPTX，不依赖外部 PPT Agent、Kimi API Key、Agent ID 或 Environment ID。
- 无客户模板时生成标准商务方案页；有客户模板时保留原页并追加方案页。首版不自动猜测或改写客户模板的占位符。
- 生成文件继续保存为 `PPT_EXPORT` 版本，复用既有下载、提交和中标/未中标项目状态流。

## 后果

- 删除 Kimi 集成、配置和测试，新增 `python-pptx` 运行依赖与本地渲染器测试；无数据库 Schema、Migration、接口或权限变化。
- 本机可稳定验证 PPTX 包结构、可编辑文本和表格；视觉样式以后可随真实客户模板增加专用渲染策略。
