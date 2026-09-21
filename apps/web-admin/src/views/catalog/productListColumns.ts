import type { ProductListItem } from "../../types/catalog"

export const FIXED_PRODUCT_LIST_COLUMNS = ["image", "sku", "product_name"] as const

export type ProductListColumnFormat = "money" | "percent" | "date" | "datetime" | "status" | "text"
export type ProductListOptionalColumnKey =
  | "company_name"
  | "listed_at"
  | "brand"
  | "model"
  | "category"
  | "item_number"
  | "jd_same_product_url"
  | "supplier"
  | "cost_price"
  | "market_price"
  | "jd_price"
  | "agreement_price"
  | "agreement_purchase_price"
  | "profit"
  | "jd_margin"
  | "deduction_review"
  | "gross_margin"
  | "purchasing_agent"
  | "barcode_text"
  | "certification_3c_code"
  | "product_specification"
  | "selling_points"
  | "packaging_list"
  | "warranty_period"
  | "remark"
  | "discount_rate"
  | "restricted_regions"
  | "jd_self_operated_price"
  | "reference_url"
  | "storefront_type"
  | "sales_volume"
  | "positive_rating"
  | "price_inflation_rate"
  | "tax_code"
  | "invoice_name"
  | "tax_category"
  | "shipping_courier"
  | "after_sales_policy"
  | "status"
  | "updated_at"

export type ProductListOptionalColumn = {
  key: ProductListOptionalColumnKey
  label: string
  prop: keyof ProductListItem
  minWidth: number
  format: ProductListColumnFormat
}

export const PRODUCT_LIST_OPTIONAL_COLUMNS: readonly ProductListOptionalColumn[] = [
  { key: "company_name", label: "所属公司", prop: "company_name", minWidth: 150, format: "text" },
  { key: "listed_at", label: "上架日期", prop: "listed_at", minWidth: 120, format: "date" },
  { key: "brand", label: "品牌", prop: "brand", minWidth: 120, format: "text" },
  { key: "model", label: "型号", prop: "model", minWidth: 150, format: "text" },
  { key: "category", label: "三级类目", prop: "category_path", minWidth: 220, format: "text" },
  { key: "item_number", label: "货号", prop: "item_number", minWidth: 140, format: "text" },
  { key: "jd_same_product_url", label: "京东同款链接", prop: "jd_same_product_url", minWidth: 220, format: "text" },
  { key: "supplier", label: "供应商", prop: "source_supplier_name", minWidth: 160, format: "text" },
  { key: "cost_price", label: "成本价", prop: "cost_price", minWidth: 125, format: "money" },
  { key: "market_price", label: "市场价", prop: "market_price", minWidth: 125, format: "money" },
  { key: "jd_price", label: "京东价", prop: "jd_price", minWidth: 125, format: "money" },
  { key: "agreement_price", label: "协议价", prop: "agreement_price", minWidth: 125, format: "money" },
  { key: "agreement_purchase_price", label: "协议价采购价", prop: "agreement_purchase_price", minWidth: 145, format: "money" },
  { key: "profit", label: "利润", prop: "profit", minWidth: 125, format: "money" },
  { key: "jd_margin", label: "京东价毛利", prop: "jd_margin", minWidth: 125, format: "percent" },
  { key: "deduction_review", label: "扣点复核", prop: "deduction_review", minWidth: 125, format: "percent" },
  { key: "gross_margin", label: "毛利率", prop: "gross_margin", minWidth: 115, format: "percent" },
  { key: "purchasing_agent", label: "采销员", prop: "purchasing_agent", minWidth: 120, format: "text" },
  { key: "barcode_text", label: "69码", prop: "barcode_text", minWidth: 150, format: "text" },
  { key: "certification_3c_code", label: "3C编码", prop: "certification_3c_code", minWidth: 150, format: "text" },
  { key: "product_specification", label: "产品规格", prop: "product_specification", minWidth: 180, format: "text" },
  { key: "selling_points", label: "卖点", prop: "selling_points", minWidth: 180, format: "text" },
  { key: "packaging_list", label: "包装清单", prop: "packaging_list", minWidth: 180, format: "text" },
  { key: "warranty_period", label: "质保期", prop: "warranty_period", minWidth: 140, format: "text" },
  { key: "remark", label: "备注", prop: "remark", minWidth: 180, format: "text" },
  { key: "discount_rate", label: "折扣率", prop: "discount_rate", minWidth: 105, format: "percent" },
  { key: "restricted_regions", label: "限售区域", prop: "restricted_regions", minWidth: 180, format: "text" },
  { key: "jd_self_operated_price", label: "京东自营前台价", prop: "jd_self_operated_price", minWidth: 155, format: "money" },
  { key: "reference_url", label: "参考链接", prop: "reference_url", minWidth: 220, format: "text" },
  { key: "storefront_type", label: "店铺类型", prop: "storefront_type", minWidth: 170, format: "text" },
  { key: "sales_volume", label: "销量", prop: "sales_volume", minWidth: 100, format: "text" },
  { key: "positive_rating", label: "好评率", prop: "positive_rating", minWidth: 105, format: "percent" },
  { key: "price_inflation_rate", label: "价格虚高比例", prop: "price_inflation_rate", minWidth: 145, format: "percent" },
  { key: "tax_code", label: "税收编码", prop: "tax_code", minWidth: 150, format: "text" },
  { key: "invoice_name", label: "开票名称", prop: "invoice_name", minWidth: 180, format: "text" },
  { key: "tax_category", label: "税收分类", prop: "tax_category", minWidth: 150, format: "text" },
  { key: "shipping_courier", label: "发货快递", prop: "shipping_courier", minWidth: 140, format: "text" },
  { key: "after_sales_policy", label: "售后政策", prop: "after_sales_policy", minWidth: 200, format: "text" },
  { key: "status", label: "状态", prop: "status", minWidth: 100, format: "status" },
  { key: "updated_at", label: "最后更新时间", prop: "updated_at", minWidth: 180, format: "datetime" },
] as const

export const PRODUCT_LIST_OPTIONAL_COLUMN_KEYS = PRODUCT_LIST_OPTIONAL_COLUMNS.map(({ key }) => key)
const DEFAULT_OPTIONAL_COLUMN_KEYS: readonly ProductListOptionalColumnKey[] = [
  "brand", "company_name", "purchasing_agent", "category", "supplier", "cost_price", "agreement_price", "discount_rate", "sales_volume", "status", "updated_at",
]

function isOptionalColumnKey(value: unknown): value is ProductListOptionalColumnKey {
  return typeof value === "string" && PRODUCT_LIST_OPTIONAL_COLUMN_KEYS.includes(value as ProductListOptionalColumnKey)
}

export function restoreProductListOptionalColumns(raw: string | null): ProductListOptionalColumnKey[] {
  try {
    const value = JSON.parse(raw ?? "[]")
    if (!Array.isArray(value)) return [...DEFAULT_OPTIONAL_COLUMN_KEYS]
    const result: ProductListOptionalColumnKey[] = []
    for (const key of value) {
      if (isOptionalColumnKey(key) && !result.includes(key)) result.push(key)
    }
    return result.length ? result : [...DEFAULT_OPTIONAL_COLUMN_KEYS]
  } catch { return [...DEFAULT_OPTIONAL_COLUMN_KEYS] }
}

export function updateProductListOptionalColumns(
  selected: ProductListOptionalColumnKey[], key: ProductListOptionalColumnKey, checked: boolean,
): ProductListOptionalColumnKey[] {
  if (checked) return selected.includes(key) ? selected : [...selected, key]
  return selected.filter((item) => item !== key)
}
