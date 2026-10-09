# Handoff：类型 1–3 工作流拆分

## 已完成

- 类型 1–5 独立业务类型、Migration 和创建 UI。
- 四份真实样表的确定性识别与解析。
- 类型 1 品牌可替换匹配；类型 2 精确同品自动最低价选择和原表回填；类型 3 类目提取和商品大表默认模板。
- 类型 3 导出保护未映射客户单元格。

## 待完成

- 未识别客户模板的可视化输入字段映射；目前会保持 `MAPPING_REQUIRED`。
- 类型 2 价格有效期和 88 折承诺尚未形成独立字段；业务已明确当前不做替代品推荐。
- 类型 3 当前一次导出选择一个目标 Sheet，尚未按客户模板多个业务 Sheet 自动分流。
- 商品主数据尚无冻结的 B/C 品来源字段，无法可靠执行 B/C 95/90 折规则；每三级类目 100 个和每品牌 10 个 SKU 也应在来源字段确认后一起落确定性校验。

## 验证入口

- `python -m pytest tests/bid tests/matching tests/recommendation -q`
- `python -m ruff check app/modules/bid app/modules/matching app/modules/recommendation tests/bid tests/matching tests/recommendation`
- `python -m mypy app/modules/bid app/modules/matching app/modules/recommendation`
- `npm run typecheck && npm run test -- --run src/views/bid src/api/bid.spec.ts src/api/recommendation.spec.ts && npm run build`
