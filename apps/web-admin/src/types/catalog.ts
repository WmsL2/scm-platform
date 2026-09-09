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
  model: string | null
  sku: string | null
  product_name: string | null
  item_number: string | null
  category_id: string
  category_path: string
  source_supplier_id: string
  source_supplier_name: string | null
  cost_price: string
  agreement_price: string | null
  jd_price: string | null
  updated_at: string
}

export interface ProductDetail extends Omit<ProductListItem, "category_path"> {
  image_reference: string | null
  category: CategorySummary
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
}

export interface ProductPage {
  items: ProductListItem[]
  total: number
  page: number
  page_size: number
}
