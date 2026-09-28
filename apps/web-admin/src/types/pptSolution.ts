export type PptGenerationStatus = "QUEUED" | "RUNNING" | "SUCCEEDED" | "FAILED"

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
  output_file_id: string | null
  status: PptGenerationStatus
  provider: string
  model: string
  prompt_version: string
  error: string | null
  created_at: string
  updated_at: string
}
