import { http } from "../shared/http/runtime"
import type {
  ProductCategoryFilterOption,
  ProductCategoryFilterOptionPage,
  ProductDetail,
  ProductExportColumnKey,
  ProductImportConfirmResult,
  ProductImportPreview,
  ProductImportSupplierCandidate,
  ProductListParams,
  ProductPage,
  ProductLifecycleResult,
  ProductPurgeResult,
  ProductSourceSupplierCandidate,
  ProductUpdatePayload,
} from "../types/catalog"

function path(suffix = ""): string {
  return `/api/v1/products${suffix}`
}

function listQuery(params: ProductListParams): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (Array.isArray(value)) {
      for (const item of value) query.append(key, item)
    } else if (value !== undefined && value !== "") query.set(key, String(value))
  }
  const serialized = query.toString()
  return serialized ? `?${serialized}` : ""
}

export const productApi = {
  list(params: ProductListParams = {}): Promise<ProductPage> {
    return http.get<ProductPage>(path(listQuery(params)))
  },

  categoryFilterOptions(
    level: ProductCategoryFilterOption["level"],
    keyword = "",
    offset = 0,
    categorySelections: string[] = [],
    status: ProductListParams["status"] = "ACTIVE",
  ): Promise<ProductCategoryFilterOptionPage> {
    const query = new URLSearchParams({ level, limit: "50", offset: String(offset), status })
    if (keyword.trim()) query.set("keyword", keyword.trim())
    for (const selection of categorySelections) query.append("category_selections", selection)
    return http.get<ProductCategoryFilterOptionPage>(path(`/category-filter-options?${query}`))
  },

  get(id: string): Promise<ProductDetail> {
    return http.get<ProductDetail>(path(`/${id}`))
  },

  updateCost(id: string, costPrice: string): Promise<ProductDetail> {
    return http.patch<ProductDetail, { cost_price: string }>(path(`/${id}/cost-price`), {
      cost_price: costPrice,
    })
  },

  update(id: string, payload: ProductUpdatePayload): Promise<ProductDetail> {
    return http.patch<ProductDetail, ProductUpdatePayload>(path(`/${id}`), payload)
  },

  updateImage(id: string, file: File): Promise<ProductDetail> {
    const form = new FormData()
    form.append("file", file)
    return http.post<ProductDetail, FormData>(path(`/${id}/image`), form)
  },

  clearImage(id: string): Promise<ProductDetail> {
    return http.delete<ProductDetail>(path(`/${id}/image`))
  },

  disable(id: string): Promise<ProductLifecycleResult> {
    return http.post<ProductLifecycleResult>(path(`/${id}/commands/disable`))
  },

  enable(id: string): Promise<ProductLifecycleResult> {
    return http.post<ProductLifecycleResult>(path(`/${id}/commands/enable`))
  },

  purge(id: string): Promise<ProductPurgeResult> {
    return http.delete<ProductPurgeResult, { confirm: true }>(path(`/${id}`), { confirm: true })
  },

  sourceSupplierCandidates(): Promise<ProductSourceSupplierCandidate[]> {
    return http.get<ProductSourceSupplierCandidate[]>(path("/source-supplier-candidates"))
  },

  previewImport(file: File): Promise<ProductImportPreview> {
    const form = new FormData()
    form.append("file", file)
    return http.post<ProductImportPreview, FormData>(path("/imports/preview"), form, {
      timeoutMs: 900_000,
    })
  },

  downloadImportTemplate(): Promise<Blob> {
    return http.getBlob(path("/imports/template"))
  },
  exportSelected(productIds: string[], columns: ProductExportColumnKey[]): Promise<Blob> {
    return http.postBlob(path("/export"), { product_ids: productIds, columns }, { timeoutMs: 60_000 })
  },

  getImportPreview(
    taskId: string,
    params: {
      page?: number
      page_size?: number
      row_status?: "ALL" | "PASSED" | "UPDATE" | "FAILED"
    } = {},
  ): Promise<ProductImportPreview> {
    return http.get<ProductImportPreview>(path(`/imports/${taskId}${listQuery(params)}`))
  },

  importSupplierCandidates(): Promise<ProductImportSupplierCandidate[]> {
    return http.get<ProductImportSupplierCandidate[]>(path("/imports/supplier-candidates"))
  },

  resolveImportSupplier(
    taskId: string,
    matchId: string,
    supplierId: string,
  ): Promise<ProductImportPreview> {
    return http.post<ProductImportPreview, { supplier_id: string }>(
      path(`/imports/${taskId}/supplier-matches/${matchId}/resolve`),
      { supplier_id: supplierId },
    )
  },

  confirmImport(taskId: string): Promise<ProductImportConfirmResult> {
    return http.post<ProductImportConfirmResult>(
      path(`/imports/${taskId}/confirm`),
      undefined,
      { timeoutMs: 900_000 },
    )
  },

  discardImport(taskId: string): Promise<{ id: string; status: "EXPIRED" }> {
    return http.post<{ id: string; status: "EXPIRED" }>(path(`/imports/${taskId}/discard`))
  },
}
