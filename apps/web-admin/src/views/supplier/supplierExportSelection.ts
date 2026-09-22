export function mergeSupplierPageSelection(
  selected: Set<string>, pageIds: string[], current: string[],
): Set<string> {
  const pageIdSet = new Set(pageIds)
  const currentIdSet = new Set(current)
  const result = new Set([...selected].filter((id) => !pageIdSet.has(id) || currentIdSet.has(id)))
  for (const id of current) result.add(id)
  return result
}

export function isAllSuppliersSelected(selected: Set<string>, total: number): boolean {
  return total > 0 && selected.size === total
}

export function clearSupplierSelection(): Set<string> { return new Set() }
