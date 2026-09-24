import type { BidProjectFile } from "./bid"
import { PRODUCT_EXPORT_COLUMN_DEFINITIONS } from "./catalog"

export type RecommendationRunStatus = "DRAFT" | "QUEUED" | "ANALYZING" | "RETRIEVING" | "RANKING" | "CANDIDATES_READY" | "WAITING_CONFIRMATION" | "CONFIRMED" | "EXPORTED" | "FAILED" | "NO_CANDIDATES" | "NEEDS_INPUT" | "CANCELLED"

export interface RecommendationTemplateFile extends BidProjectFile { mapping_confirmed: boolean }
export interface RecommendationTemplateMappingUpdate { sheet_name: string; header_row: number; data_start_row: number; mapping_json: Record<string, string> }
export interface RecommendationTemplateMapping extends RecommendationTemplateMappingUpdate { template_file: BidProjectFile; confirmed_by: string | null; confirmed_at: string | null }
export interface RecommendationTemplateColumn { column_index: number; header: string; duplicate: boolean }
export interface RecommendationTemplateStructure { sheet_names: string[]; sheet_name: string; header_row: number; max_row: number; columns: RecommendationTemplateColumn[] }
export interface ParsedRequirement { gross_margin_min: string | null; jd_price_min: string | null; jd_price_max: string | null; category_keywords: string[]; brand_keywords: string[]; scenario_keywords: string[]; fulfillment_mode: string | null }
export interface RecommendationCategoryChoice { id: string; level1_name: string | null; level2_name: string | null; level3_name: string | null; reason: string | null; candidate_count: number }
export type FactoryDirectStatus = "PENDING" | "YES" | "NO"
export interface RecommendationConfirmation { id: string; campaign_price: string | null; fulfillment: string | null; evidence: string | null; factory_direct: FactoryDirectStatus; confirmed_by: string | null; confirmed_at: string | null }
export interface RecommendationCandidate { id: string; product_id: string; rank: number; score: string | null; reason: string | null; product_snapshot: Record<string, unknown>; supplier_snapshot: Record<string, unknown>; price_snapshot: Record<string, unknown>; factory_direct: FactoryDirectStatus | null; confirmation: RecommendationConfirmation | null }
export interface RecommendationRun { id: string; project_id: string; status: RecommendationRunStatus; progress_percent?: number; progress_message?: string | null; raw_requirement_snapshot: string; parsed_requirement: ParsedRequirement | null; provider: string | null; model: string | null; prompt_version: string | null; error: string | null; category_choices: RecommendationCategoryChoice[]; candidates: RecommendationCandidate[]; created_at: string; updated_at: string }
export interface RecommendationConfirmationUpdate { campaign_price?: string | null; delivery_status?: string | null; inventory_status?: string | null; factory_direct?: FactoryDirectStatus; fulfillment_cycle?: string | null; evidence?: string | null }

export const RUN_STATUS_LABELS: Record<RecommendationRunStatus, string> = {
  DRAFT: "草稿", QUEUED: "排队中", ANALYZING: "分析需求中", RETRIEVING: "检索商品中",
  RANKING: "候选排序中", CANDIDATES_READY: "候选已生成", WAITING_CONFIRMATION: "待人工确认",
  CONFIRMED: "已确认", EXPORTED: "已导出", FAILED: "执行失败", NO_CANDIDATES: "暂无候选",
  NEEDS_INPUT: "需要补充信息", CANCELLED: "已取消",
}

export const TEMPLATE_MAPPING_FIELDS: Array<{ key: string; label: string }> = [
  ...PRODUCT_EXPORT_COLUMN_DEFINITIONS,
  { key: "factory_direct", label: "是否厂直（人工确认）" },
]
