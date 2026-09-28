import type { BidProjectStatus, BidProjectType } from "./bid"

export interface DashboardRecentProject {
  id: string
  project_code: string
  project_name: string
  project_type: BidProjectType
  status: BidProjectStatus
  updated_at: string
}

export interface DashboardSummary {
  formal_product_count: number
  normal_supplier_count: number
  active_project_count: number
  pending_supplier_count: number
  recent_projects: DashboardRecentProject[]
}
