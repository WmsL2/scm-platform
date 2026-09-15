import { http } from "../shared/http/runtime"
import type { Category, CategoryImportResult, CategoryPayload } from "../types/category"

export const categoryApi = {
  list(activeOnly = false): Promise<Category[]> { return http.get<Category[]>(`/api/v1/categories${activeOnly ? "?active_only=true" : ""}`) },
  create(payload: CategoryPayload): Promise<Category> { return http.post<Category, CategoryPayload>("/api/v1/categories", payload) },
  update(id: string, payload: CategoryPayload): Promise<Category> { return http.put<Category, CategoryPayload>(`/api/v1/categories/${id}`, payload) },
  remove(id: string): Promise<void> { return http.delete<void>(`/api/v1/categories/${id}`) },
  import(file: File): Promise<CategoryImportResult> { const body = new FormData(); body.append("file", file); return http.post<CategoryImportResult, FormData>("/api/v1/categories/imports", body) },
  template(): Promise<Blob> { return http.getBlob("/api/v1/categories/imports/template") },
}
