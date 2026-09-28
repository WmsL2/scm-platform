# 类型 5 PPT 方案交接

## 当前状态

代码、Migration、Web 工作台和测试已经完成首版。类型 5 可以创建项目、运行 Kimi 推荐、人工确认商品、组合套装并创建 PPT 生成任务。

## 部署前必须完成

1. 在后端环境变量填写 `KIMI_API_KEY`、`KIMI_PPT_AGENT_ID`、`KIMI_ENVIRONMENT_ID`。
2. 执行 `alembic upgrade head`，目标 Revision 为 `20260928_0041`。
3. 使用真实甲方 PPT 模板分别验证“项目模板”和“系统默认模板”两条生成路径。
4. 检查 Hosted Agent 返回 Artifact 的实际字段与下载地址；若企业租户 API 契约不同，只调整 `integrations/kimi/client.py`，不要把供应商协议泄漏进业务 Service。
5. 正式部署建议将 `TASK_MODE` 接入可用的后台队列；当前 Local-First `inline` 会等待 Kimi 生成请求完成。

## 已知边界

- 首版生成输入携带商品冻结快照中的图片引用，尚未把本地商品图片作为 Kimi 资源逐张上传；局域网本地图片 URL 对外部模型不可访问时，PPT 可能缺少商品图。
- 默认模板当前由固定生成指令约束为简洁商务版式，尚未内置一份版本化的默认 `.pptx` 文件。
- 未使用真实企业凭据完成端到端 PPTX 验收。
