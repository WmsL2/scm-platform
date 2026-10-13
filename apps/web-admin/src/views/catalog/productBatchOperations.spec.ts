import { expect, it } from "vitest"
import productListSource from "./ProductListView.vue?raw"

it("keeps product batch edit, featured marking and lifecycle operations in the product list", () => {
  expect(productListSource).toContain("批量修改")
  expect(productListSource).toContain("batchChangeStatus")
  expect(productListSource).toContain("batchDisable")
  expect(productListSource).toContain("batchEnable")
  expect(productListSource).toContain("设为主推")
  expect(productListSource).toContain("取消主推")
  expect(productListSource).toContain("productApi.batchUpdate")
  expect(productListSource).toContain("productApi.batchDisable")
  expect(productListSource).toContain("productApi.batchEnable")
})
