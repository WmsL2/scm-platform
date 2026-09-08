export type ArchiveStatus = "DRAFT" | "PENDING" | "ARCHIVED"
export type CooperationStatus = "NORMAL" | "STOPPED" | "BLACKLIST"
export type SupplierCommand = "submit" | "archive" | "stop" | "blacklist"

export interface SupplierContactInput {
  contact_name: string | null
  contact_phone: string | null
}

export interface SupplierContact extends SupplierContactInput {
  id: string
}

export interface SupplierFormDraft {
  supplier_name: string
  main_brands: string
  advantage: string
  contacts: SupplierContactInput[]
}

export interface SupplierListItem {
  id: string
  supplier_code: string
  supplier_name: string
  main_brands: string
  advantage: string
  archive_status: ArchiveStatus
  cooperation_status: CooperationStatus
}

export interface SupplierDetail extends SupplierListItem {
  contacts: SupplierContact[]
  archived_by: string | null
  archived_at: string | null
  created_at: string
  updated_at: string
}

export interface SupplierPage {
  items: SupplierListItem[]
  total: number
  page: number
  page_size: number
}

export interface SupplierDeleteResult {
  id: string
  status: "deleted"
}

export interface SupplierImportRow {
  source_row_number: number
  supplier_name: string | null
  main_brands: string | null
  advantage: string | null
  contact_name: string | null
  contact_phone: string | null
  is_valid: boolean
  error_message: string | null
}

export interface SupplierImportPreview {
  id: string
  original_filename: string
  status: "VALIDATED"
  total_rows: number
  valid_rows: number
  invalid_rows: number
  rows: SupplierImportRow[]
}

export interface SupplierImportConfirmResult {
  id: string
  status: "CONFIRMED"
  imported_count: number
}

export interface SupplierListParams {
  page?: number
  page_size?: number
  keyword?: string
  archive_status?: ArchiveStatus
  cooperation_status?: CooperationStatus
}

export const ARCHIVE_STATUS_LABELS: Record<ArchiveStatus, string> = {
  DRAFT: "草稿",
  PENDING: "待归档",
  ARCHIVED: "已归档",
}

export const COOPERATION_STATUS_LABELS: Record<CooperationStatus, string> = {
  NORMAL: "正常合作",
  STOPPED: "已停用",
  BLACKLIST: "黑名单",
}

export function createSupplierFormDraft(): SupplierFormDraft {
  return {
    supplier_name: "",
    main_brands: "",
    advantage: "",
    contacts: [],
  }
}

export function supplierDetailToDraft(supplier: SupplierDetail): SupplierFormDraft {
  return {
    supplier_name: supplier.supplier_name,
    main_brands: supplier.main_brands,
    advantage: supplier.advantage,
    contacts: supplier.contacts.map((contact) => ({
      contact_name: contact.contact_name,
      contact_phone: contact.contact_phone,
    })),
  }
}

export function normalizeSupplierDraft(draft: SupplierFormDraft): SupplierFormDraft {
  return {
    supplier_name: draft.supplier_name.trim(),
    main_brands: draft.main_brands.trim(),
    advantage: draft.advantage.trim(),
    contacts: draft.contacts
      .map((contact) => ({
        contact_name: contact.contact_name?.trim() || null,
        contact_phone: contact.contact_phone?.trim() || null,
      }))
      .filter((contact) => contact.contact_name || contact.contact_phone),
  }
}

export function supplierDraftValidationMessage(draft: SupplierFormDraft): string | undefined {
  const normalized = normalizeSupplierDraft(draft)
  if (!normalized.supplier_name) return "请填写供应商名称"
  if (!normalized.main_brands) return "请填写主营品牌"
  if (!normalized.advantage) return "请填写主要优势"
  return undefined
}

export function commandRequiresReason(command: SupplierCommand): boolean {
  return command === "stop" || command === "blacklist"
}
