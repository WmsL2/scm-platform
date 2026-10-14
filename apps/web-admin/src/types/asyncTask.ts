export type AsyncTaskStatus = "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELLED"

export const ASYNC_TASK_KIND_LABELS: Record<string, string> = {
  TYPE1_MATCH: "类型1规格匹配", TYPE2_MATCH: "类型2同品比价",
  TYPE3_CANDIDATE_GENERATION: "类型3候选生成", TYPE4_RECOMMENDATION_AGENT: "类型4推品",
  TYPE5_RECOMMENDATION_GENERATION: "类型5推品", TYPE5_PPT_GENERATION: "PPT生成",
  MAPPING_STRUCTURE_ANALYSIS: "Excel结构解析",
}

export interface AsyncTask {
  id: string
  project_id: string
  run_id: string | null
  task_kind: string
  status: AsyncTaskStatus
  progress_percent: number
  attempt_count: number
  max_attempts: number
  progress_message: string | null
  error_code: string | null
  error_message: string | null
  heartbeat_at: string | null
  created_at: string
  created_by: string
  cancel_requested_at?: string | null
  cancel_requested_by?: string | null
}

export interface AsyncTaskPage {
  items: AsyncTask[]
  total: number
  page: number
  page_size: number
}
