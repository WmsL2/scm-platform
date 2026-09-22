export type ProductMutationRefreshOptions = {
  resetToFirstPage?: boolean
  rowRemoved?: boolean
}

export function productMutationRefreshPage(
  currentPage: number,
  currentPageItemCount: number,
  options: ProductMutationRefreshOptions = {},
): number {
  if (options.resetToFirstPage) return 1
  if (options.rowRemoved && currentPageItemCount === 1 && currentPage > 1) return currentPage - 1
  return currentPage
}

export function acceptsProductListResponse(sequence: number, currentSequence: number): boolean {
  return sequence === currentSequence
}
