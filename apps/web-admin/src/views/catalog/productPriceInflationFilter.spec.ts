import { expect, it } from "vitest"

import productListSource from "./ProductListView.vue?raw"

it("wires the price-inflation percentage range into product-list requests", () => {
  expect(productListSource).toContain('label="价格虚高比例区间（%）"')
  expect(productListSource).toContain(
    "price_inflation_rate_min: percentQuery(filters.price_inflation_rate_min)",
  )
  expect(productListSource).toContain(
    "price_inflation_rate_max: percentQuery(filters.price_inflation_rate_max)",
  )
})
