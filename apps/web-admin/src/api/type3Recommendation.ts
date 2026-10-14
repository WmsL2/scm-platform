import { http } from "../shared/http/runtime"
import type { AsyncTask } from "../types/asyncTask"

const base = "/api/v1/type3-recommendation-projects"
export type Type3Level = "LEVEL1" | "LEVEL2" | "LEVEL3"
export interface Type3Node { node_id: string; coordinate: string; level: Type3Level; label: string; code: string | null }
export interface Type3Sheet { sheet_name: string; header_row: number; data_start_row: number; max_row: number; max_column: number; mapping_json: Record<string, unknown>; nodes: Type3Node[] }
export interface Type3Preview { template_file_id: string; sheets: Type3Sheet[] }
export interface Type3OutputColumn { column_index: number; header: string; duplicate: boolean }
export interface Type3SheetOutputStructure { sheet_name: string; header_row: number; max_row: number; columns: Type3OutputColumn[] }
export interface Type3ExportField { key: string; label: string }
export interface Type3RunSheetSummary { sheet_name: string; selected_node_count: number }
export interface Type3Run { id: string; project_id: string; project_status: string | null; status: string; raw_remark_snapshot: string; error: string | null; sheet_summaries: Type3RunSheetSummary[]; created_at: string }
export interface Type3Candidate { id: string; sheet_name: string; product_id: string; rank: number; product_snapshot: Record<string, unknown>; supplier_snapshot: Record<string, unknown>; price_snapshot: Record<string, unknown>; confirmed_at: string | null }
export interface Type3CandidatePage { items: Type3Candidate[]; total: number; confirmed_total: number; page: number; page_size: number }
export interface Type3CandidateSheetSummary { sheet_name: string; total: number; confirmed_total: number }
export interface Type3CandidateQuery { page: number; pageSize: number; sheetName?: string }
export interface Type3CandidateConfirmation { candidate_ids?: string[]; select_all_unconfirmed?: boolean; excluded_candidate_ids?: string[]; sheet_name?: string }
export interface Type3CandidateUnconfirmation { candidate_ids?: string[]; select_all_confirmed?: boolean; excluded_candidate_ids?: string[]; sheet_name?: string }

export const type3RecommendationApi = {
  preview: (projectId: string) => http.get<Type3Preview | AsyncTask>(`${base}/${projectId}/template-preview`),
  sheetOutputStructure: (projectId: string, params: { sheetName: string; headerRow: number }) => http.get<Type3SheetOutputStructure | AsyncTask>(`${base}/${projectId}/sheet-output-structure?sheet_name=${encodeURIComponent(params.sheetName)}&header_row=${params.headerRow}`),
  exportFields: (projectId: string) => http.get<Type3ExportField[]>(`${base}/${projectId}/export-fields`),
  savedSelections: (projectId: string) => http.get<Type3Sheet[]>(`${base}/${projectId}/sheet-selections`),
  saveSelections: (projectId: string, sheets: Type3Sheet[]) => http.put<Type3Sheet[]>(`${base}/${projectId}/sheet-selections`, { sheets }),
  async start(projectId: string, sheets: Type3Sheet[]): Promise<Type3Run> {
    const task = await http.post<AsyncTask>(`${base}/${projectId}/runs`, { sheets })
    if (!task.run_id) throw new Error("任务创建成功但缺少类型 3 运行标识")
    return http.get<Type3Run>(`${base}/runs/${task.run_id}`)
  },
  runs: (projectId: string) => http.get<Type3Run[]>(`${base}/${projectId}/runs`),
  run: (runId: string) => http.get<Type3Run>(`${base}/runs/${runId}`),
  candidates: (runId: string, query: Type3CandidateQuery) => http.get<Type3CandidatePage>(`${base}/runs/${runId}/candidates?page=${query.page}&page_size=${query.pageSize}${query.sheetName ? `&sheet_name=${encodeURIComponent(query.sheetName)}` : ""}`),
  candidateSheets: (runId: string) => http.get<Type3CandidateSheetSummary[]>(`${base}/runs/${runId}/candidate-sheets`),
  confirm: (candidateIds: string[]) => http.post<boolean>(`${base}/candidates/confirm`, candidateIds),
  confirmCandidates: (runId: string, payload: Type3CandidateConfirmation) => http.post<number>(`${base}/runs/${runId}/candidate-confirmations`, payload),
  unconfirmCandidates: (runId: string, payload: Type3CandidateUnconfirmation) => http.post<number>(`${base}/runs/${runId}/candidate-unconfirmations`, payload),
  completeSelection: (projectId: string, runId: string) => http.post<boolean>(`${base}/${projectId}/runs/${runId}/commands/complete-selection`),
  reopenSelection: (projectId: string, runId: string) => http.post<boolean>(`${base}/${projectId}/runs/${runId}/commands/reopen-selection`),
  export: (projectId: string, runId: string) => http.post<{ id: string; original_filename: string }>(`${base}/${projectId}/runs/${runId}/exports`),
  download: (runId: string, fileId: string) => http.getBlob(`${base}/runs/${runId}/exports/${fileId}/download`),
}
