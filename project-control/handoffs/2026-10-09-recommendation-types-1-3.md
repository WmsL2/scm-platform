# Handoff：类型 1–3 工作流拆分

## 已完成

- 类型 1–5 独立业务类型、Migration 和创建 UI。
- 四份真实样表的确定性识别与解析。
- 类型 1 品牌可替换匹配；类型 2 独立 AI 综合整行与备注执行原品优先、无原品才同类型替代、自动最低合规价选择和原表回填；类型 3 类目提取和商品大表默认模板。
- 类型 3 导出保护未映射客户单元格。
- 类型 2 已完成大表候选构建性能优化：搜索文档与品牌目录任务级复用、每行 AI 候选最多 8 条、失败批次取消其余请求；288 行 × 7,246 商品只读基准为 9.614 秒。

## 待完成

- 类型 1、3 未识别客户模板的可视化输入字段映射；类型 2 已支持 AI 字段映射，失败时保持 `MAPPING_REQUIRED`。
- 类型 2 商品主数据仍无可靠价格有效期字段，不能自动填写有效期；折扣比例从需求行非空内容或项目备注动态解析后，按商品折扣率确定性校验，空白结果列表头不触发。
- 类型 3 当前一次导出选择一个目标 Sheet，尚未按客户模板多个业务 Sheet 自动分流。
- 商品主数据尚无冻结的 B/C 品来源字段，无法可靠执行 B/C 95/90 折规则；每三级类目 100 个和每品牌 10 个 SKU 也应在来源字段确认后一起落确定性校验。

## 验证入口

- `python -m pytest tests/bid tests/matching tests/recommendation -q`
- `python -m ruff check app/modules/bid app/modules/matching app/modules/recommendation tests/bid tests/matching tests/recommendation`
- `python -m mypy app/modules/bid app/modules/matching app/modules/recommendation`
- `npm run typecheck && npm run test -- --run src/views/bid src/api/bid.spec.ts src/api/recommendation.spec.ts && npm run build`
