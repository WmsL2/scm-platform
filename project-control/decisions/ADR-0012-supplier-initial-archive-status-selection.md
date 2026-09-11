# ADR-0012：供应商初始与编辑归档状态可选

状态：ACCEPTED
日期：2026-09-11

## 背景

原有 Supplier Excel 导入固定创建 `ARCHIVED + NORMAL` 供应商，新建供应商固定创建为 `DRAFT + NORMAL`。业务需要在实际新建、导入确认和后续编辑时选择合适的归档状态。

## 决策

- `POST /api/v1/suppliers` 的 `archive_status` 可选，默认仍为 `DRAFT`；调用方可选择 `DRAFT`、`PENDING` 或 `ARCHIVED`。
- `POST /api/v1/suppliers/imports/{batch_id}/confirm` 的请求体可选择本批初始 `archive_status`，默认仍为 `ARCHIVED`，以兼容既有 API 调用。
- `PATCH /api/v1/suppliers/{supplier_id}` 可更新 `archive_status`；供应商编码与合作状态仍不能通过通用编辑接口修改。
- 初始或编辑结果为 `ARCHIVED` 时，服务端写入当前操作人的 `archived_by`、`archived_at`；选择 `DRAFT` 或 `PENDING` 时清空这两个归档审计字段。
- Excel 导入的合作状态仍固定为 `NORMAL`。商品导入匹配规则不变，只有 `ARCHIVED + NORMAL + not deleted` 的供应商可作为来源供应商。

## 结果

新增、编辑和 Excel 导入确认页面均展示归档状态选择。Excel 仍必须先完成逐行校验预览，再由上传者选择状态并显式确认，不能静默入库。

本决策不新增数据库字段、Migration 或权限码；创建/导入继续需要 `supplier:create`，编辑需要 `supplier:update`。
