# Handoff：自由推品底座（A → B/C）

## Migration 与所有权

唯一 Revision 为 `20260923_0039`，down_revision 为 `20260922_0038`，当前为单 Head。
它包含所有已知 Recommendation 表和权限。B/C 禁止为这些已有字段重复创建 Migration；确需新增字段时，先向 A 提交 Migration Requirement。

A-owned：该 Revision、Bid project/file/import type 基座、`recommendation/template/`、权限 seed、Bid 路由聚合点和项目控制集成文档。B-owned：recommendation domain/repository/service/export/router。C-owned：DeepSeek、AgentRunner、jobs、Web。`recommendation_router.py` 属于 B；A5 仅负责最终 include/register，不重写其路由。

## 枚举

- `BidProjectType`：`FILTER_RECOMMENDATION`、`FREE_RECOMMENDATION`、`PPT_SOLUTION`。
- `BidImportStatus`：`PARSED`、`MAPPING_REQUIRED`、`FAILED`、`NOT_REQUIRED`。
- `BidFileType`：`ORIGINAL`、`QUOTED_EXPORT`、`RECOMMENDATION_TEMPLATE`。
- `RecommendationRunStatus`：`DRAFT`、`QUEUED`、`ANALYZING`、`RETRIEVING`、`RANKING`、`CANDIDATES_READY`、`WAITING_CONFIRMATION`、`CONFIRMED`、`EXPORTED`、`FAILED`、`NO_CANDIDATES`、`NEEDS_INPUT`、`CANCELLED`。

## Database contract

- `scm_recommendation_template_mapping`：`id` UUID PK；`project_id` UUID NOT NULL FK Bid Project RESTRICT（index）；`template_file_id` UUID NOT NULL FK Bid File RESTRICT（UNIQUE、index）；`template_sha256` varchar(64)；`sheet_name` varchar(128)；`header_row`/`data_start_row` integer；`mapping_json` JSON；`confirmed_by` UUID nullable；`confirmed_at` datetime nullable；审计 `created_at`/`updated_at` NOT NULL。
- `scm_recommendation_run`：`id` UUID PK；`project_id` UUID NOT NULL FK Bid Project RESTRICT（非 UNIQUE，index）；`status` varchar(32) NOT NULL CHECK；`raw_requirement_snapshot` TEXT NOT NULL；`parsed_requirement` JSON nullable；`provider` varchar(64)、`model` varchar(128)、`prompt_version` varchar(64)、`error` TEXT 均 nullable；`created_by` UUID NOT NULL；审计时间 NOT NULL。索引：project、status、created_at。
- `scm_recommendation_category_choice`：`id` UUID PK；`run_id` UUID NOT NULL FK Run RESTRICT（index）；三级文本路径均 nullable；`source` varchar(32) NOT NULL；`reason` TEXT nullable；`candidate_count` integer NOT NULL default 0；`created_at` NOT NULL。没有 `category_id`。
- `scm_recommendation_candidate`：`id` UUID PK；`run_id` UUID NOT NULL FK Run RESTRICT（index）；`product_id` UUID NOT NULL FK Product RESTRICT（index）；`rank` integer NOT NULL；`score` decimal(9,4) nullable；`reason` TEXT、`manual_flags` JSON nullable；三种 JSON snapshot 均 NOT NULL；`created_at` NOT NULL；UNIQUE(`run_id`,`product_id`) 及 (`run_id`,`rank`) index。
- `scm_recommendation_confirmation`：`id` UUID PK；`candidate_id` UUID NOT NULL FK Candidate RESTRICT UNIQUE；`campaign_price` decimal(65,30) nullable；履约字符串、`evidence`、确认人/时间均 nullable；审计时间 NOT NULL。

## Permissions

仅现有非删除 `boss` 默认获授：`recommendation:create`（A 模板/类型4创建，C 创建页）、`recommendation:run`（B Run）、`recommendation:detail`（B/C 详情）、`recommendation:review`（B 人工确认）、`recommendation:export`（B 导出）。

## API contract

- `POST /api/v1/bid-projects`：省略 `project_type` 时维持 FILTER，需 `bid:create` 和客户 `.xlsx`。FREE 需 `bid:create` + `recommendation:create`、至少 20 字 `remark` 和 `recommendation_template` `.xlsx`；不建 Item，返回 `project_type=FREE_RECOMMENDATION`、`import_status=NOT_REQUIRED`。PPT 固定拒绝。
- `POST /api/v1/bid-projects/{project_id}/recommendation-templates`：仅 FREE、`recommendation:create`、multipart `recommendation_template`；追加 `RECOMMENDATION_TEMPLATE` 版本和未确认 Mapping。
- `GET /api/v1/bid-projects/{project_id}/recommendation-templates`：仅返回此项目的模板版本和 `mapping_confirmed`。
- `GET/PATCH /api/v1/bid-projects/{project_id}/recommendation-templates/{file_id}/mapping`：PATCH 请求为 `sheet_name`、`header_row`、`data_start_row`、`mapping_json`；响应含 `template_file`、上述映射、`confirmed_by`、`confirmed_at`。PATCH 读取精确 storage_key 的工作簿校验，成功后由服务端写确认人/时间。

Mapping target whitelist：`category_level1_name`、`category_level2_name`、`category_level3_name`、`brand`、`sku`、`product_name`、`jd_price`、`agreement_price`、`discount_rate`、`purchasing_agent`、`profit`、`gross_margin`、`factory_direct`、`shipping_courier`。自动映射不包括“毛利”、厂直或物流推断。

错误码：`BID_PROJECT_TYPE_NOT_AVAILABLE`、`FREE_RECOMMENDATION_REMARK_REQUIRED`、`RECOMMENDATION_TEMPLATE_REQUIRED`、`RECOMMENDATION_TEMPLATE_INVALID`、`RECOMMENDATION_TEMPLATE_NOT_ALLOWED`、`RECOMMENDATION_TEMPLATE_NOT_FOUND`、`RECOMMENDATION_TEMPLATE_PROJECT_MISMATCH`、`RECOMMENDATION_TEMPLATE_MAPPING_INVALID`、`RECOMMENDATION_TEMPLATE_MAPPING_NOT_CONFIRMED`、`PROJECT_TYPE_NOT_SUPPORTED`。

## Fixture 示例

FREE multipart：`project_name=2026自由推品`、`buyer_name=客户A`、`project_type=FREE_RECOMMENDATION`、`remark=需要一套适合企业办公场景的可靠设备组合方案`、`recommendation_template=@recommendation.xlsx`。

Mapping response：`{"template_file":{"id":"<uuid>","file_type":"RECOMMENDATION_TEMPLATE","version_no":1},"sheet_name":"推荐清单","header_row":1,"data_start_row":2,"mapping_json":{"brand":"品牌"},"confirmed_by":null,"confirmed_at":null}`。

PATCH：`{"sheet_name":"推荐清单","header_row":1,"data_start_row":2,"mapping_json":{"brand":"品牌","product_name":"名称"}}`。B 创建 Run 时应使用 FREE Project 的 `id`、`remark` 作为 requirement snapshot，并保持项目和 Run 生命周期独立。
