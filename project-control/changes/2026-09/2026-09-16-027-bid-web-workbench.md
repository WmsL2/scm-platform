# Change Record: Bid Web Workbench

Date: 2026-09-16
Module: bid / matching / quotation

## Delivered

- Added server-side requirement-item keyword filtering and a joined current-selection snapshot read model; item pagination does not issue selection N+1 queries.
- Raised the retained project-item limit to 100,000.
- Added request-level HTTP timeouts and the complete bid API client.
- Added bid project list/create, detail/timeline/files, and matching workbench pages with permission-gated lifecycle actions.
- Workbench loads candidate records only when a user opens a row; it displays persisted selection snapshots rather than re-querying Product or Supplier masters.

## Validation

- Backend full suite: 160 passed; Ruff and mypy full checks passed.
- Frontend suite: 20 files / 74 tests passed; typecheck and production build passed.
- Browser acceptance is partially verified: the local application reaches the real login page. Authenticated MAPPING_REQUIRED creation is blocked by unavailable test credentials and by the missing configured BidTemplate; no database template was fabricated.

## Database

新增 Revision `20260916_0025`，为历史兼容的 `scm_bid_project.start_at` 可空业务开始时间；它与用户填写的 `deadline_at` 和系统审计 `created_at` 明确分离。

## Follow-up: Project edit and business void

- 新增 `bid:update`、`bid:void` 与 boss 初始化授权（Revision `20260916_0026`）。
- 新增受状态限制的基础信息编辑和业务作废 API/UI；作废需保留原因并写入 `PROJECT_VOIDED`，不会删除项目、行、快照、文件或事件。
- `VOIDED` 为终态。由于既有项目状态带 MySQL CHECK 约束，新增 Revision `20260916_0027` 将 `VOIDED` 加入约束，确保业务状态可真实持久化。
- 详情页同时提供并按状态/权限控制匹配、导出、提交、结果登记、编辑和作废操作；终态项目仅保留历史查看和下载能力。
