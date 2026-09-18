import type { ProductCategoryFilterOption } from "../../types/catalog"

function unique(values: string[]): string[] {
  return Array.from(new Set(values)).sort((left, right) => left.localeCompare(right, "zh-CN"))
}

export function derivedLevel1Keys(
  optionsByKey: Map<string, ProductCategoryFilterOption>,
  level2Keys: string[],
  level3Keys: string[],
): string[] {
  return unique([...level2Keys, ...level3Keys]
    .map((key) => optionsByKey.get(key)?.level1_selection_key)
    .filter((key): key is string => Boolean(key)))
}

export function derivedLevel2Keys(
  optionsByKey: Map<string, ProductCategoryFilterOption>,
  level3Keys: string[],
): string[] {
  return unique(level3Keys
    .map((key) => optionsByKey.get(key)?.level2_selection_key)
    .filter((key): key is string => Boolean(key)))
}

export function visibleSelection(explicitValues: string[], derivedValues: string[]): string[] {
  return unique([...explicitValues, ...derivedValues])
}

export function updateExplicitSelection(
  explicitValues: string[],
  visibleValues: string[],
  nextValues: string[],
  derivedValues: string[],
): string[] {
  const next = new Set(nextValues)
  const visible = new Set(visibleValues)
  const derived = new Set(derivedValues)
  return unique([
    ...explicitValues.filter((value) => next.has(value)),
    ...nextValues.filter((value) => !visible.has(value) && !derived.has(value)),
  ])
}
