import { http } from "../shared/http/runtime"
import type { BidCandidate, BidFileType, BidItemPage, BidItemStatus, BidProjectCreateResult, BidProjectDetail, BidProjectFile, BidProjectPage, BidProjectStatus, BidProjectStatusResult, BidProjectType, BidSelectionResult, NoQuoteReason, StartMatchingResult } from "../types/bid"
import type { RecommendationTemplateFile, RecommendationTemplateMapping, RecommendationTemplateMappingUpdate, RecommendationTemplateStructure } from "../types/recommendation"
const base = "/api/v1/bid-projects"
function query(values: Record<string, string | number | undefined>): string { const params = new URLSearchParams(); Object.entries(values).forEach(([key, value]) => { if (value !== undefined && String(value).trim() !== "") params.set(key, String(value)) }); const value = params.toString(); return value ? `?${value}` : "" }
export const bidApi = {
  list(params: { page?: number; page_size?: number; keyword?: string; status?: BidProjectStatus } = {}): Promise<BidProjectPage> { return http.get(`${base}${query(params)}`) },
  get(id: string): Promise<BidProjectDetail> { return http.get(`${base}/${id}`) },
  update(id: string, body: { project_name: string; buyer_name: string; start_at: string | null; deadline_at: string | null; remark: string | null }): Promise<BidProjectDetail> { return http.patch(`${base}/${id}`, body) },
  create(input: { project_type: BidProjectType; file?: File; recommendation_template?: File; project_name: string; buyer_name: string; start_at?: string; deadline_at?: string; remark?: string }): Promise<BidProjectCreateResult> { const form = new FormData(); form.append("project_type", input.project_type); if (input.file) form.append("file", input.file); if (input.recommendation_template) form.append("recommendation_template", input.recommendation_template); form.append("project_name", input.project_name); form.append("buyer_name", input.buyer_name); if (input.start_at) form.append("start_at", input.start_at); if (input.deadline_at) form.append("deadline_at", input.deadline_at); if (input.remark?.trim()) form.append("remark", input.remark.trim()); return http.post(`${base}`, form, { timeoutMs: 300_000 }) },
  recommendationTemplates(id: string): Promise<RecommendationTemplateFile[]> { return http.get(`${base}/${id}/recommendation-templates`) },
  recommendationTemplateMapping(id: string, fileId: string): Promise<RecommendationTemplateMapping> { return http.get(`${base}/${id}/recommendation-templates/${fileId}/mapping`) },
  recommendationTemplateStructure(id: string, fileId: string, params: { sheet_name?: string; header_row: number }): Promise<RecommendationTemplateStructure> { return http.get(`${base}/${id}/recommendation-templates/${fileId}/structure${query(params)}`) },
  updateRecommendationTemplateMapping(id: string, fileId: string, body: RecommendationTemplateMappingUpdate): Promise<RecommendationTemplateMapping> { return http.patch(`${base}/${id}/recommendation-templates/${fileId}/mapping`, body) },
  items(id: string, params: { page?: number; page_size?: number; status?: BidItemStatus; keyword?: string } = {}): Promise<BidItemPage> { return http.get(`${base}/${id}/items${query(params)}`) },
  files(id: string): Promise<BidProjectFile[]> { return http.get(`${base}/${id}/files`) },
  download(id: string, fileId: string): Promise<Blob> { return http.getBlob(`${base}/${id}/files/${fileId}/download`) },
  startMatching(id: string): Promise<StartMatchingResult> { return http.post(`${base}/${id}/commands/start-matching`, undefined, { timeoutMs: 300_000 }) },
  candidates(id: string, itemId: string): Promise<BidCandidate[]> { return http.get(`${base}/${id}/items/${itemId}/candidates`) },
  select(id: string, itemId: string, body: { candidate_id: string; selected_unit_price: string; note?: string }): Promise<BidSelectionResult> { return http.post(`${base}/${id}/items/${itemId}/selections`, body.note?.trim() ? body : { candidate_id: body.candidate_id, selected_unit_price: body.selected_unit_price }) },
  noQuote(id: string, itemId: string, body: { reason: NoQuoteReason; reason_detail?: string }): Promise<BidSelectionResult> { return http.post(`${base}/${id}/items/${itemId}/no-quote`, body.reason_detail?.trim() ? body : { reason: body.reason }) },
  export(id: string): Promise<BidProjectFile> { return http.post(`${base}/${id}/exports`, undefined, { timeoutMs: 300_000 }) },
  submit(id: string, body: { submitted_file_id: string; note?: string }): Promise<BidProjectStatusResult> { return http.post(`${base}/${id}/commands/submit`, body.note?.trim() ? body : { submitted_file_id: body.submitted_file_id }) },
  win(id: string, note?: string): Promise<BidProjectStatusResult> { return http.post(`${base}/${id}/commands/win`, note?.trim() ? { note: note.trim() } : undefined) },
  lose(id: string, note?: string): Promise<BidProjectStatusResult> { return http.post(`${base}/${id}/commands/lose`, note?.trim() ? { note: note.trim() } : undefined) },
  voidProject(id: string, body: { reason: string }): Promise<BidProjectStatusResult> { return http.post(`${base}/${id}/commands/void`, body) },
}
