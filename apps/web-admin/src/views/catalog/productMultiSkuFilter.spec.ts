import { describe, expect, it } from "vitest"

import { parseMultipleSkus } from "./productMultiSkuFilter"
import productListSource from "./ProductListView.vue?raw"

describe("multiple SKU filter", () => {
  it("splits whitespace, Chinese or English commas, semicolons and line breaks then removes duplicates", () => {
    expect(parseMultipleSkus(" SKU-1，SKU-2\nSKU-3; SKU-1；SKU-4,SKU-5 ")).toEqual([
      "SKU-1", "SKU-2", "SKU-3", "SKU-4", "SKU-5",
    ])
  })

  it("wires the parsed values into the product-list request", () => {
    expect(productListSource).toContain('label="多个 SKU"')
    expect(productListSource).toContain("skus: parseMultipleSkus(filters.skus)")
    expect(productListSource).toContain("@keydown.ctrl.enter.prevent=\"searchProducts\"")
  })
})
