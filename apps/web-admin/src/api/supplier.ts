import { http } from "../shared/http/runtime"
import type {
  SupplierCommand,
  ArchiveStatus,
  SupplierDetail,
  SupplierDeleteResult,
  SupplierFormDraft,
  SupplierImportConfirmResult,
  SupplierImportPreview,
  SupplierListParams,
  SupplierPage,
} from "../types/supplier"

function supplierPath(path = ""): string {
  return `/api/v1/suppliers${path}`
}

function listQuery(params: SupplierListParams): string {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") query.set(key, String(value))
  }
  const serialized = query.toString()
  return serialized ? `?${serialized}` : ""
}

export const supplierApi = {
  list(params: SupplierListParams = {}): Promise<SupplierPage> {
    return http.get<SupplierPage>(supplierPath(listQuery(params)))
  },

  get(id: string): Promise<SupplierDetail> {
    return http.get<SupplierDetail>(supplierPath(`/${id}`))
  },

  create(payload: SupplierFormDraft): Promise<SupplierDetail> {
    return http.post<SupplierDetail, SupplierFormDraft>(supplierPath(), payload)
  },

  update(id: string, payload: SupplierFormDraft): Promise<SupplierDetail> {
    return http.patch<SupplierDetail, SupplierFormDraft>(supplierPath(`/${id}`), payload)
  },

  command(id: string, command: SupplierCommand, reason?: string): Promise<SupplierDetail> {
    return http.post<SupplierDetail, { reason: string } | undefined>(
      supplierPath(`/${id}/commands/${command}`),
      reason === undefined ? undefined : { reason },
    )
  },

  delete(id: string): Promise<SupplierDeleteResult> {
    return http.delete<SupplierDeleteResult>(supplierPath(`/${id}`))
  },

  downloadImportTemplate(): Promise<Blob> {
    return http.getBlob(supplierPath("/imports/template"))
  },

  previewImport(file: File): Promise<SupplierImportPreview> {
    const formData = new FormData()
    formData.append("file", file)
    return http.post<SupplierImportPreview, FormData>(supplierPath("/imports/preview"), formData)
  },

  confirmImport(batchId: string, archiveStatus: ArchiveStatus): Promise<SupplierImportConfirmResult> {
    return http.post<SupplierImportConfirmResult, { archive_status: ArchiveStatus }>(
      supplierPath(`/imports/${batchId}/confirm`),
      { archive_status: archiveStatus },
    )
  },
}
