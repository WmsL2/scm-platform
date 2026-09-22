import { describe, expect, it } from "vitest"
import productListSource from "./ProductListView.vue?raw"
import {
  acceptsProductListResponse,
  productMutationRefreshPage,
} from "./productListRefresh"

describe("product list mutation refresh", () => {
  it("uses the unified refresh entry point for every product-list mutation", () => {
    expect(productListSource).toContain("await refreshProductsAfterMutation({ resetToFirstPage: true })")
    expect(productListSource.match(/await refreshProductsAfterMutation\(\{\n      rowRemoved: true,\n    \}\)/g)).toHaveLength(3)
  })

  it("resets import refresh to the first page", () => {
    expect(productMutationRefreshPage(4, 20, { resetToFirstPage: true })).toBe(1)
  })

  it("closes every successful confirm without a secondary preview GET or discard", () => {
    const confirmBody = productListSource.match(/async function confirmImport[\s\S]*?\n}\n\nasync function closeImportDialog/)?.[0] ?? ""
    expect(confirmBody).toContain("finishImportDialog()")
    expect(confirmBody).not.toContain("loadImportRows(1)")
    expect(confirmBody).not.toContain('result.status === "CONFIRMED"')
  })

  it("refreshes the current page before a normal dialog close", () => {
    const closeBody = productListSource.match(/async function closeImportDialog[\s\S]*?\n}\n\nfunction finishImportDialog/)?.[0] ?? ""
    expect(closeBody.indexOf("await refreshProductsAfterMutation()")).toBeGreaterThan(-1)
    expect(closeBody.indexOf("importDialogVisible.value = false")).toBeGreaterThan(closeBody.indexOf("await refreshProductsAfterMutation()"))
  })

  it("clears confirmed preview state before closing so @closed cannot discard it", () => {
    const finishBody = productListSource.match(/function finishImportDialog[\s\S]*?\n}\n\nasync function discardImportPreview/)?.[0] ?? ""
    expect(finishBody.indexOf("importPreview.value = undefined")).toBeLessThan(finishBody.indexOf("importDialogVisible.value = false"))
  })

  it.each(["disable", "enable", "purge"])("moves %s from a one-row page to the prior page", () => {
    expect(productMutationRefreshPage(3, 1, { rowRemoved: true })).toBe(2)
  })

  it("retains the current page when its removal does not empty it", () => {
    expect(productMutationRefreshPage(3, 2, { rowRemoved: true })).toBe(3)
  })

  it("clears cross-page selected IDs before refreshing", () => {
    expect(productListSource).toMatch(
      /async function refreshProductsAfterMutation[\s\S]*?selectedProductIds\.value\.clear\(\)[\s\S]*?await loadProducts\(targetPage\)/,
    )
  })

  it("rejects a late response from an older list request", () => {
    expect(acceptsProductListResponse(4, 5)).toBe(false)
    expect(acceptsProductListResponse(5, 5)).toBe(true)
  })
})
