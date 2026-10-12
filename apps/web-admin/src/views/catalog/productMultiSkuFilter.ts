const MULTI_SKU_SEPARATOR = /[\s,，;；]+/

export function parseMultipleSkus(value: string): string[] {
  return [...new Set(value.split(MULTI_SKU_SEPARATOR).map((item) => item.trim()).filter(Boolean))]
}
