export type PptGenerationStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED"
export type PptRecommendationMode = "SINGLE" | "COMBINATION" | "MIXED"
export interface PptPriceBand { min_price: string | null; max_price: string; item_count: number }
export interface PptRecommendationConfig {
  project_id: string
  recommendation_mode: PptRecommendationMode
  price_bands: PptPriceBand[]
  fulfillment_deadline: string | null
  created_at: string
  updated_at: string
}

export interface PptPriceBandAvailability {
  price_band_index: number
  min_price: string | null
  max_price: string
  candidate_count: number
  required_count: number
  can_generate: boolean
  generated_plan_count: number
  requested_plan_count: number
  failure_reason: string | null
  message: string
}

export interface PptSolutionPlan {
  id: string
  run_id: string
  price_band_index: number
  plan_no: number
  plan_type: "SINGLE" | "COMBINATION"
  name: string
  summary: string | null
  candidate_ids: string[]
  is_selected: boolean
  selected_by: string | null
  selected_at: string | null
  items: PptSolutionPlanItem[]
  created_at: string
}

export interface PptSolutionPlanItem {
  candidate_id: string
  rank: number
  product_snapshot: Record<string, unknown>
  price_snapshot: Record<string, unknown>
}

export interface PptPackageItemInput { candidate_id: string; quantity: number }
export interface PptPackageItem {
  id: string
  candidate_id: string
  quantity: number
  unit_price: string
  line_total: string
  sort_order: number
  product_snapshot: Record<string, unknown>
  price_snapshot: Record<string, unknown>
}
export interface PptPackage {
  id: string
  run_id: string
  name: string
  price_tier: string | null
  total_price: string
  reason: string | null
  is_selected: boolean
  items: PptPackageItem[]
  created_at: string
  updated_at: string
}
export interface PptGenerationTask {
  id: string
  project_id: string
  run_id: string
  template_file_id: string | null
  template_code: string
  template_version: string
  output_file_id: string | null
  status: PptGenerationStatus
  provider: string
  model: string
  prompt_version: string
  error: string | null
  created_at: string
  updated_at: string
}
export interface PptTemplate {
  template_code: string
  name: string
  description: string
  preview_url: string | null
  version: string
  is_available: boolean
}
