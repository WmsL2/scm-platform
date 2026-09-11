export interface CategorySummary {
  id: string
  source_type: string
  level1_name: string
  level2_name: string
  level3_name: string
  deduction_rate: string
  is_active: boolean
}

export interface ProductListItem {
  id: string
  listed_at: string | null
  brand: string | null
  image_reference: string | null
  model: string | null
  sku: string | null
  product_name: string | null
  item_number: string | null
  category_id: string | null
  category_path: string
  source_supplier_id: string
  source_supplier_name: string | null
  cost_price: string
  agreement_price: string | null
  jd_price: string | null
  updated_at: string
}

export interface ProductDetail extends Omit<ProductListItem, "category_path"> {
  category: CategorySummary | null
  category_level1_name: string | null
  category_level2_name: string | null
  category_level3_name: string | null
  jd_same_product_url: string | null
  market_price: string | null
  agreement_purchase_price: string | null
  profit: string | null
  jd_margin: string | null
  purchasing_agent: string | null
  barcode_text: string | null
  deduction_review: string | null
  product_specification: string | null
  selling_points: string | null
  gross_margin: string | null
  remark: string | null
  discount_rate: string | null
  restricted_regions: string | null
  jd_self_operated_price: string | null
  reference_url: string | null
  storefront_type: string | null
  price_inflation_rate: string | null
  deduction_rate: string | null
  created_at: string
}

export interface ProductListParams {
  page?: number
  page_size?: number
  keyword?: string
  category_id?: string
  source_supplier_id?: string
}

export interface ProductPage {
  items: ProductListItem[]
  total: number
  page: number
  page_size: number
}

export interface ProductDeleteResult {
  id: string
  status: "deleted"
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
  category_path: string
  category_id: string | null
  supplier_match_id: string | null
  is_valid: boolean
  error_message: string | null
  warning_message: string | null
}

export interface ProductImportPreview {
  id: string
  original_filename: string
  status: "VALIDATED" | "NEEDS_RESOLUTION" | "READY_TO_CONFIRM" | "CONFIRMED"
  total_rows: number
  valid_rows: number
  invalid_rows: number
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
  listed_at: string | null
  brand: string | null
  image_reference: string | null
  model: string | null
  sku: string
  product_name: string | null
  item_number: string | null
  jd_same_product_url: string | null
  purchasing_agent: string | null
  source_supplier_id: string
  barcode_text: string | null
  product_specification: string | null
  selling_points: string | null
  remark: string | null
  restricted_regions: string | null
  reference_url: string | null
  storefront_type: string | null
}

export interface ProductImportConfirmResult {
  id: string
  status: "CONFIRMED"
  imported_count: number
  restored_count: number
}
