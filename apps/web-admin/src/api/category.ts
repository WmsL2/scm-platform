import { http } from "../shared/http/runtime"
import type { Category, CategoryFilterOption, CategoryFilterOptionPage, CategoryImportResult, CategoryListParams, CategoryPage, CategoryPayload } from "../types/category"

export const categoryApi = {
  selection(): Promise<Category[]> { return http.get<Category[]>("/api/v1/categories/selection") },
  filterOptions(level: CategoryFilterOption["level"], keyword = "", offset = 0): Promise<CategoryFilterOptionPage> { const query = new URLSearchParams({ level, limit: "50", offset: String(offset) }); if (keyword.trim()) query.set("keyword", keyword.trim()); return http.get<CategoryFilterOptionPage>(`/api/v1/categories/filter-options?${query}`) },
  list(params: CategoryListParams = {}): Promise<CategoryPage> { const q = new URLSearchParams({ page: String(params.page ?? 1), page_size: String(params.page_size ?? 20) }); for (const [key, value] of Object.entries(params)) if (value !== undefined && key !== "page" && key !== "page_size") q.set(key, String(value)); return http.get<CategoryPage>(`/api/v1/categories?${q}`) },
  create(payload: CategoryPayload): Promise<Category> { return http.post<Category, CategoryPayload>("/api/v1/categories", payload) },
  update(id: string, payload: CategoryPayload): Promise<Category> { return http.put<Category, CategoryPayload>(`/api/v1/categories/${id}`, payload) },
  remove(id: string): Promise<void> { return http.delete<void>(`/api/v1/categories/${id}`) },
  import(file: File, deductionRatePercent: string): Promise<CategoryImportResult> { const body = new FormData(); body.append("file", file); body.append("deduction_rate_percent", deductionRatePercent); return http.post<CategoryImportResult, FormData>("/api/v1/categories/imports", body) },
  template(): Promise<Blob> { return http.getBlob("/api/v1/categories/imports/template") },
}
