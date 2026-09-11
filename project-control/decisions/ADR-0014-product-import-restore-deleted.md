# ADR-0014：商品导入确认恢复同键已删除商品

状态：ACCEPTED
日期：2026-09-11

## 背景

`scm_product` 使用 `source_supplier_id + sku` 作为防重业务键，逻辑删除后该键仍保留。业务需要重新导入同一商品时恢复原记录，而不是创建第二条记录或要求人工改库。

## 决策

- 商品大表预览中，同键正常 Product 仍为错误并阻止 Confirm；同键仅有逻辑删除 Product 时显示恢复警告，可进入 Confirm。
- 上传者显式 Confirm 后，服务端在同一事务内锁定原 Product，并将 `is_deleted` 设为 `false`、`deleted_by` 和 `deleted_at` 清空、`updated_by` 更新为当前操作人。
- 恢复保留原 Product ID、`source_supplier_id + sku` 和全部既有商品业务字段；Excel 行不覆盖原商品字段，也不新增 Product。
- Confirm 返回新增数量和恢复数量。无需新增权限、数据库字段或 Migration；恢复仍要求既有 `product:import` 权限和有效来源供应商。

## 结果

本 ADR 收窄 ADR-0013 中“未来恢复策略”的范围：仅固定商品大表 Confirm 支持恢复同键已删除商品。普通页面/API 恢复、已删除 SKU 复用及覆盖式重新导入均不在本次范围内。
