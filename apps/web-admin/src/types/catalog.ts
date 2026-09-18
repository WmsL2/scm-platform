export type ProductStatus = "ACTIVE" | "DISABLED"

export interface ProductListItem {
  id: string
  company_name: string | null
  listed_at: string | null
  brand: string | null
  image_reference: string | null
  model: string | null
  sku: string | null
  product_name: string | null
  item_number: string | null
  jd_same_product_url: string | null
  category_path: string
  source_supplier_id: string
  source_supplier_name: string | null
  cost_price: string
  agreement_price: string | null
  jd_price: string | null
  market_price: string | null
  agreement_purchase_price: string | null
  profit: string | null
  jd_margin: string | null
  deduction_review: string | null
  gross_margin: string | null
  purchasing_agent: string | null
  barcode_text: string | null
  certification_3c_code: string | null
  product_specification: string | null
  selling_points: string | null
  packaging_list: string | null
  warranty_period: string | null
  restricted_regions: string | null
  jd_self_operated_price: string | null
  storefront_type: string | null
  reference_url: string | null
  sales_volume: number | null
  positive_rating: string | null
  discount_rate: string | null
  price_inflation_rate: string | null
  tax_code: string | null
  invoice_name: string | null
  tax_category: string | null
  shipping_courier: string | null
  after_sales_policy: string | null
  remark: string | null
  status: ProductStatus
  created_by: string | null
  created_by_username: string | null
  created_at: string
  updated_by: string | null
  updated_by_username: string | null
  updated_at: string
}

export interface ProductDetail extends Omit<
  ProductListItem,
  "category_path" | "created_by" | "created_by_username" | "updated_by" | "updated_by_username"
> {
  category_level1_name: string | null
  category_level2_name: string | null
  category_level3_name: string | null
  deduction_rate: string | null
}

export interface ProductListParams {
  page?: number
  page_size?: number
  keyword?: string
  company_name?: string
  purchasing_agent?: string
  brand?: string
  supplier_name?: string
  category_level1_name?: string
  category_level2_name?: string
  category_selections?: string[]
  source_supplier_id?: string
  cost_price_min?: string
  cost_price_max?: string
  agreement_price_min?: string
  agreement_price_max?: string
  discount_rate_min?: string
  discount_rate_max?: string
  sales_volume_min?: string
  sales_volume_max?: string
  status?: ProductStatus
}

export interface ProductCategoryFilterOption {
  selection_key: string
  label: string
  level: "LEVEL1" | "LEVEL2" | "LEVEL3"
  level1_selection_key: string
  level2_selection_key: string
  level1_label: string
  level2_label: string
}

export interface ProductCategoryFilterOptionPage {
  items: ProductCategoryFilterOption[]
  has_more: boolean
}

export interface ProductPage {
  items: ProductListItem[]
  total: number
  page: number
  page_size: number
}

export interface ProductLifecycleResult {
  id: string
  status: ProductStatus
}

export interface ProductPurgeResult {
  id: string
  status: "PURGED"
}

export interface ProductImportSupplierMatch {
  id: string
  supplier_name_normalized: string
  match_status: "MATCHED" | "AMBIGUOUS" | "UNMATCHED" | "INELIGIBLE"
  match_method: "NAME_EXACT" | "MANUAL" | null
  matched_supplier_id: string | null
  matched_supplier_code: string | null
  matched_supplier_name: string | null
}

export interface ProductImportRow {
  source_row_number: number
  product_name: string | null
  supplier_name_raw: string | null
  image_saved: boolean
  image_pending_save: boolean
  category_path: string
  supplier_match_id: string | null
  is_valid: boolean
  write_action: "CREATE" | "UPDATE"
  changed_fields: string[] | null
  is_imported: boolean
  error_message: string | null
  warning_message: string | null
}

export interface ProductImportPreview {
  id: string
  original_filename: string
  status: "VALIDATED" | "NEEDS_RESOLUTION" | "READY_TO_CONFIRM" | "PARTIALLY_CONFIRMED" | "CONFIRMED"
  total_rows: number
  valid_rows: number
  update_rows: number
  invalid_rows: number
  imported_rows: number
  rows: ProductImportRow[]
  supplier_matches: ProductImportSupplierMatch[]
}

export interface ProductImportSupplierCandidate {
  id: string
  supplier_code: string
  supplier_name: string
  main_brands: string
}

export interface ProductSourceSupplierCandidate {
  id: string
  supplier_code: string
  supplier_name: string
  main_brands: string
}

export interface ProductUpdatePayload {
  company_name: string | null
  listed_at: string | null
  brand: string | null
  model: string | null
  product_name: string | null
  category_level1_name: string
  category_level2_name: string
  category_level3_name: string
  item_number: string | null
  jd_same_product_url: string | null
  cost_price: string
  market_price: string | null
  jd_price: string | null
  agreement_price: string | null
  agreement_purchase_price: string | null
  profit: string | null
  jd_margin: string | null
  deduction_review: string | null
  gross_margin: string | null
  purchasing_agent: string | null
  barcode_text: string | null
  certification_3c_code: string | null
  product_specification: string | null
  selling_points: string | null
  packaging_list: string | null
  warranty_period: string | null
  remark: string | null
  restricted_regions: string | null
  reference_url: string | null
  storefront_type: string | null
  sales_volume: number | null
  positive_rating: string | null
  discount_rate: string | null
  price_inflation_rate: string | null
  jd_self_operated_price: string | null
  tax_code: string | null
  invoice_name: string | null
  tax_category: string | null
  shipping_courier: string | null
  after_sales_policy: string | null
}

export interface ProductImportConfirmResult {
  id: string
  status: "PARTIALLY_CONFIRMED" | "CONFIRMED"
  imported_count: number
  created_count: number
  updated_count: number
  imported_rows: number
  valid_rows: number
  update_rows: number
  invalid_rows: number
}
