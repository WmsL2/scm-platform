export type BidProjectStatus = "IMPORTED" | "MATCHING" | "SELECTING" | "READY" | "EXPORTED" | "SUBMITTED" | "WON" | "LOST" | "VOIDED"
export type BidImportStatus = "PARSED" | "MAPPING_REQUIRED" | "FAILED" | "NOT_REQUIRED"
export type BidProjectType = "FILTER_RECOMMENDATION" | "FREE_RECOMMENDATION" | "PPT_SOLUTION"
export type BidItemStatus = "PENDING" | "NO_MATCH" | "UNIQUE_MATCH" | "MULTIPLE_MATCH" | "SELECTED" | "NO_QUOTE"
export type BidFileType = "ORIGINAL" | "QUOTED_EXPORT" | "RECOMMENDATION_TEMPLATE"
export type NoQuoteReason = "NO_PRODUCT_MATCH" | "BRAND_MODEL_MISMATCH" | "PRICE_NOT_MATCH" | "SUPPLIER_UNAVAILABLE" | "OTHER"

export interface BidProjectListItem { id: string; project_code: string; project_name: string; buyer_name: string; start_at: string | null; deadline_at: string | null; status: BidProjectStatus; import_status: BidImportStatus; project_type: BidProjectType; total_item_count: number; processed_item_count: number; created_at: string }
export interface BidProjectFile { id: string; file_type: BidFileType; version_no: number; original_filename: string; file_size: number; sha256: string; created_at: string }
export interface BidProjectEvent { id: string; from_status: BidProjectStatus | null; to_status: BidProjectStatus | null; event_type: string; actor_id: string | null; note: string | null; occurred_at: string }
export interface BidProjectDetail extends BidProjectListItem { remark: string | null; template_id: string | null; template_version: number | null; import_error: string | null; submitted_file_id: string | null; files: BidProjectFile[]; events: BidProjectEvent[] }
export interface BidProjectCreateResult { id: string; project_code: string; status: BidProjectStatus; import_status: BidImportStatus; project_type: BidProjectType; import_error: string | null; template_id: string | null; template_version: number | null; total_item_count: number }
export interface BidCurrentSelection { selection_id: string; product_id: string; supplier_id: string; selected_unit_price: string; requirement_snapshot: Record<string, unknown>; product_snapshot: Record<string, unknown>; supplier_snapshot: Record<string, unknown>; price_snapshot: Record<string, unknown>; note: string | null; created_at: string }
export interface BidProjectItem { id: string; sheet_name: string; source_row_number: number; product_name: string | null; brand: string | null; model: string | null; specification: string | null; category_text: string | null; quantity: string | null; unit: string | null; max_price: string | null; buyer_item_code: string | null; status: BidItemStatus; current_selection_id: string | null; no_quote_reason: string | null; current_selection: BidCurrentSelection | null }
export interface BidCandidate { candidate_id: string; product_id: string; supplier_id: string; product_name: string | null; brand: string | null; model: string | null; category_path: string; product_specification: string | null; supplier_code: string; supplier_name: string; cost_price: string | null; jd_price: string | null; agreement_price: string | null; score: string; rank: number; method: string; match_reason: Record<string, unknown> }
export interface StartMatchingResult { task_id: string; status: string; total_item_count: number; processed_item_count: number }
export interface BidSelectionResult { selection_id: string | null; project_item_id: string; status: BidItemStatus; current_selection_id: string | null }
export interface BidProjectStatusResult { id: string; status: BidProjectStatus; submitted_file_id: string | null }
export interface BidProjectPage { items: BidProjectListItem[]; total: number; page: number; page_size: number }
export interface BidItemPage { items: BidProjectItem[]; total: number; page: number; page_size: number }
export const PROJECT_STATUS_LABELS: Record<string, string> = { IMPORTED: "已导入", MATCHING: "匹配中", SELECTING: "待选品", READY: "选品完成", EXPORTED: "已生成报价", SUBMITTED: "已投标", WON: "已中标", LOST: "未中标", VOIDED: "已作废" }
export const IMPORT_STATUS_LABELS: Record<string, string> = { PARSED: "已解析", MAPPING_REQUIRED: "待模板配置", FAILED: "导入失败", NOT_REQUIRED: "无需需求表" }
export const PROJECT_TYPE_LABELS: Record<BidProjectType, string> = { FILTER_RECOMMENDATION: "条件筛选推品", FREE_RECOMMENDATION: "自由推品 Agent", PPT_SOLUTION: "PPT 方案（暂未开放）" }
export const ITEM_STATUS_LABELS: Record<string, string> = { PENDING: "待匹配", NO_MATCH: "未匹配", UNIQUE_MATCH: "唯一候选", MULTIPLE_MATCH: "多个候选", SELECTED: "已选品", NO_QUOTE: "无法报价" }
export const FILE_TYPE_LABELS: Record<string, string> = { ORIGINAL: "原始文件", QUOTED_EXPORT: "报价文件", RECOMMENDATION_TEMPLATE: "自由推品模板" }
export const NO_QUOTE_REASON_LABELS: Record<string, string> = { NO_PRODUCT_MATCH: "无匹配商品", BRAND_MODEL_MISMATCH: "品牌或型号不满足", PRICE_NOT_MATCH: "价格不满足", SUPPLIER_UNAVAILABLE: "供应商无法供货", OTHER: "其他" }
