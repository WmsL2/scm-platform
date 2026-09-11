import { http } from "../shared/http/runtime"
import type {
  ProductDetail,
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
    if (value !== undefined && value !== "") query.set(key, String(value))
  }
  const serialized = query.toString()
  return serialized ? `?${serialized}` : ""
}

export const productApi = {
  list(params: ProductListParams = {}): Promise<ProductPage> {
    return http.get<ProductPage>(path(listQuery(params)))
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
    return http.post<ProductImportPreview, FormData>(path("/imports/preview"), form)
  },

  downloadImportTemplate(): Promise<Blob> {
    return http.getBlob(path("/imports/template"))
  },

  getImportPreview(taskId: string): Promise<ProductImportPreview> {
    return http.get<ProductImportPreview>(path(`/imports/${taskId}`))
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
    return http.post<ProductImportConfirmResult>(path(`/imports/${taskId}/confirm`))
  },
}
