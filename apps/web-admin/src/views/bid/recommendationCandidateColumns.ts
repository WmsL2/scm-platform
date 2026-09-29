import {
  PRODUCT_EXPORT_COLUMN_DEFINITIONS,
  type ProductExportColumnKey,
} from "../../types/catalog"

export const FIXED_RECOMMENDATION_CANDIDATE_COLUMNS = [
  "image_reference",
  "sku",
  "product_name",
] as const

export type RecommendationCandidateOptionalColumnKey = Exclude<
  ProductExportColumnKey,
  typeof FIXED_RECOMMENDATION_CANDIDATE_COLUMNS[number]
>

export type RecommendationCandidateColumnFormat = "money" | "percent" | "text"

export type RecommendationCandidateOptionalColumn = {
  key: RecommendationCandidateOptionalColumnKey
  label: string
  minWidth: number
  format: RecommendationCandidateColumnFormat
}

const MONEY_COLUMN_KEYS = new Set<ProductExportColumnKey>([
  "cost_price",
  "market_price",
  "jd_price",
  "agreement_price",
  "agreement_purchase_price",
  "profit",
  "jd_self_operated_price",
])

const PERCENT_COLUMN_KEYS = new Set<ProductExportColumnKey>([
  "jd_margin",
  "deduction_review",
  "gross_margin",
  "positive_rating",
  "discount_rate",
  "price_inflation_rate",
])

function formatFor(key: ProductExportColumnKey): RecommendationCandidateColumnFormat {
  if (MONEY_COLUMN_KEYS.has(key)) return "money"
  if (PERCENT_COLUMN_KEYS.has(key)) return "percent"
  return "text"
}

function minWidthFor(key: ProductExportColumnKey): number {
  if (key.includes("url") || key.includes("policy") || key === "selling_points" || key === "remark") return 200
  if (MONEY_COLUMN_KEYS.has(key)) return 125
  if (PERCENT_COLUMN_KEYS.has(key)) return 110
  if (key.includes("category")) return 150
  return 130
}

export const RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS: readonly RecommendationCandidateOptionalColumn[] =
  PRODUCT_EXPORT_COLUMN_DEFINITIONS
    .filter(({ key }) => !FIXED_RECOMMENDATION_CANDIDATE_COLUMNS.includes(key as typeof FIXED_RECOMMENDATION_CANDIDATE_COLUMNS[number]))
    .map(({ key, label }) => ({
      key: key as RecommendationCandidateOptionalColumnKey,
      label,
      minWidth: minWidthFor(key),
      format: formatFor(key),
    }))

const DEFAULT_OPTIONAL_COLUMN_KEYS: readonly RecommendationCandidateOptionalColumnKey[] = [
  "brand",
  "model",
  "category_level3_name",
  "jd_price",
  "agreement_price",
  "discount_rate",
  "gross_margin",
  "positive_rating",
]

const VALID_KEYS = new Set<string>(RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS.map(({ key }) => key))

export function restoreRecommendationCandidateOptionalColumns(
  raw: string | null,
): RecommendationCandidateOptionalColumnKey[] {
  try {
    const value: unknown = JSON.parse(raw ?? "[]")
    if (!Array.isArray(value)) return [...DEFAULT_OPTIONAL_COLUMN_KEYS]
    const restored = value.filter(
      (key): key is RecommendationCandidateOptionalColumnKey =>
        typeof key === "string" && VALID_KEYS.has(key),
    )
    return restored.length ? [...new Set(restored)] : [...DEFAULT_OPTIONAL_COLUMN_KEYS]
  } catch {
    return [...DEFAULT_OPTIONAL_COLUMN_KEYS]
  }
}

export function updateRecommendationCandidateOptionalColumns(
  selected: RecommendationCandidateOptionalColumnKey[],
  key: RecommendationCandidateOptionalColumnKey,
  checked: boolean,
): RecommendationCandidateOptionalColumnKey[] {
  if (checked) return selected.includes(key) ? selected : [...selected, key]
  return selected.filter((item) => item !== key)
}
