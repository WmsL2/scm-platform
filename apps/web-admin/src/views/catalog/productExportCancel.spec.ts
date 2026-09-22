import { describe, expect, it } from "vitest"
import productListSource from "./ProductListView.vue?raw"

describe("product export cancellation wiring", () => {
  it("uses a per-export controller and cancels every dialog close path", () => {
    expect(productListSource).toContain("const controller = new AbortController()")
    expect(productListSource).toContain("productApi.exportSelected(productIds, columns, controller.signal)")
    expect(productListSource).toContain("function cancelProductExport")
    expect(productListSource).toContain("exportAbortController?.abort()")
    expect(productListSource).toContain(":before-close=\"handleExportDialogBeforeClose\"")
  })

  it("prevents download and failure feedback after abort", () => {
    expect(productListSource).toContain("if (controller.signal.aborted) return")
    expect(productListSource).toContain('ElMessage.info("已取消商品导出")')
    expect(productListSource).toContain("if (exportAbortController === controller)")
  })
})
