import { PRODUCT_EXPORT_COLUMNS, type ProductExportColumnKey } from "../../types/catalog"

export function restoreExportColumns(raw: string | null): ProductExportColumnKey[] {
  try {
    const value = JSON.parse(raw ?? "[]")
    const valid = Array.isArray(value) ? value.filter((key): key is ProductExportColumnKey => PRODUCT_EXPORT_COLUMNS.includes(key)) : []
    return valid.length ? valid : [...PRODUCT_EXPORT_COLUMNS]
  } catch { return [...PRODUCT_EXPORT_COLUMNS] }
}

export function mergePageSelection(selected: Set<string>, pageIds: string[], current: string[]): Set<string> {
  const result = new Set(selected)
  for (const id of pageIds) result.delete(id)
  for (const id of current) result.add(id)
  return result
}
