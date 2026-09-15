import { http } from "../shared/http/runtime"
import type { Category, CategoryImportResult, CategoryPage, CategoryPayload } from "../types/category"

export const categoryApi = {
  list(page = 1, pageSize = 20, activeOnly = false): Promise<CategoryPage> { const q = new URLSearchParams({ page: String(page), page_size: String(pageSize) }); if (activeOnly) q.set("active_only", "true"); return http.get<CategoryPage>(`/api/v1/categories?${q}`) },
  create(payload: CategoryPayload): Promise<Category> { return http.post<Category, CategoryPayload>("/api/v1/categories", payload) },
  update(id: string, payload: CategoryPayload): Promise<Category> { return http.put<Category, CategoryPayload>(`/api/v1/categories/${id}`, payload) },
  remove(id: string): Promise<void> { return http.delete<void>(`/api/v1/categories/${id}`) },
  import(file: File, deductionRatePercent: string): Promise<CategoryImportResult> { const body = new FormData(); body.append("file", file); body.append("deduction_rate_percent", deductionRatePercent); return http.post<CategoryImportResult, FormData>("/api/v1/categories/imports", body) },
  template(): Promise<Blob> { return http.getBlob("/api/v1/categories/imports/template") },
}
