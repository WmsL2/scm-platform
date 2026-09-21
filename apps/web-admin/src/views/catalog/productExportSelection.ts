import { PRODUCT_EXPORT_COLUMNS, type ProductExportColumnKey } from "../../types/catalog"

export function restoreExportColumns(raw: string | null): ProductExportColumnKey[] {
  try {
    const value = JSON.parse(raw ?? "[]")
    const valid = Array.isArray(value) ? value.filter((key): key is ProductExportColumnKey => PRODUCT_EXPORT_COLUMNS.includes(key)) : []
    return valid.length ? valid : [...PRODUCT_EXPORT_COLUMNS]
  } catch { return [...PRODUCT_EXPORT_COLUMNS] }
}

export function mergePageSelection(selected: Set<string>, pageIds: string[], current: string[]): Set<string> {
  const pageIdSet = new Set(pageIds)
  const currentIdSet = new Set(current)
  const result = new Set(
    [...selected].filter((id) => !pageIdSet.has(id) || currentIdSet.has(id)),
  )
  for (const id of current) result.add(id)
  return result
}

export function isAllProductsSelected(selected: Set<string>, total: number): boolean {
  return total > 0 && selected.size === total
}

export function clearProductSelection(): Set<string> {
  return new Set()
}
