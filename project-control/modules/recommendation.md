# 自由推品 Recommendation

状态：FOUNDATION_IMPLEMENTED / B_C_HANDOFF_PENDING

- 统一 Bid Project 类型、自由推品创建合同、模板版本和字段映射 API 已由 `20260923_0039` 提供。
- Run、类目选择、候选、人工确认表仅为 B 后续 Repository/Service 预建 Schema；本模块未实现 Agent、商品检索、排序、确认或导出业务。
- 模板映射须经人工 PATCH 确认；模板文件按 `RECOMMENDATION_TEMPLATE` 递增版本保留。
- FILTER 携带自由推品模板会被拒绝；PATCH 会校验已保存工作簿的 sheet、行号和源表头。
