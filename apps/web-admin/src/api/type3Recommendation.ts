import { http } from "../shared/http/runtime"

const base = "/api/v1/type3-recommendation-projects"
export type Type3Level = "LEVEL1" | "LEVEL2" | "LEVEL3"
export interface Type3Node { node_id: string; coordinate: string; level: Type3Level; label: string; code: string | null }
export interface Type3Sheet { sheet_name: string; header_row: number; data_start_row: number; mapping_json: Record<string, unknown>; nodes: Type3Node[] }
export interface Type3Preview { template_file_id: string; sheets: Type3Sheet[] }
export interface Type3Run { id: string; project_id: string; status: string; raw_remark_snapshot: string; error: string | null; created_at: string }
export interface Type3Candidate { id: string; sheet_name: string; rank: number; product_snapshot: Record<string, unknown>; supplier_snapshot: Record<string, unknown>; price_snapshot: Record<string, unknown>; confirmed_at: string | null }
export interface Type3CandidatePage { items: Type3Candidate[]; total: number; confirmed_total: number; page: number; page_size: number }

export const type3RecommendationApi = {
  preview: (projectId: string) => http.get<Type3Preview>(`${base}/${projectId}/template-preview`),
  savedSelections: (projectId: string) => http.get<Type3Sheet[]>(`${base}/${projectId}/sheet-selections`),
  saveSelections: (projectId: string, sheets: Type3Sheet[]) => http.put<Type3Sheet[]>(`${base}/${projectId}/sheet-selections`, { sheets }),
  start: (projectId: string) => http.post<Type3Run>(`${base}/${projectId}/runs`, undefined, { timeoutMs: 300_000 }),
  runs: (projectId: string) => http.get<Type3Run[]>(`${base}/${projectId}/runs`),
  candidates: (runId: string, sheetName?: string) => http.get<Type3CandidatePage>(`${base}/runs/${runId}/candidates?page=1&page_size=100${sheetName ? `&sheet_name=${encodeURIComponent(sheetName)}` : ""}`),
  confirm: (candidateIds: string[]) => http.post<boolean>(`${base}/candidates/confirm`, candidateIds),
  completeSelection: (projectId: string, runId: string) => http.post<boolean>(`${base}/${projectId}/runs/${runId}/commands/complete-selection`),
  export: (projectId: string, runId: string) => http.post<{ id: string; original_filename: string }>(`${base}/${projectId}/runs/${runId}/exports`),
  download: (runId: string, fileId: string) => http.getBlob(`${base}/runs/${runId}/exports/${fileId}/download`),
}
