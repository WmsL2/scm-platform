# Change Record：自由推品确认编辑与导出闭环

日期：2026-09-24  
分支：`fix/recommendation-confirmation-export-loop`

## 修复

- 候选详情返回完整人工 Confirmation；前端不再伪造空确认对象，也不再使用错误的 `fulfillment` DTO 字段。
- 确认更新采用 PATCH 语义，未提交字段保持原值；确认的活动价、状态、履约说明和依据可映射到 Excel。
- 导出前清理连续模板数据区中的映射业务值，避免历史示例商品残留；空映射在模板确认阶段即拒绝。
- 已导出 Run 的确认变更遵循 lifecycle `EXPORTED -> CONFIRMED`，重新导出生成递增版本。

## Migration

无，复用 `20260923_0040`。
