export type AsyncTaskStatus = "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED" | "CANCELLED"

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
}

export interface AsyncTaskPage {
  items: AsyncTask[]
  total: number
  page: number
  page_size: number
}
