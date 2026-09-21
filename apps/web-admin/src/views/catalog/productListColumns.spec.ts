import { describe, expect, it } from "vitest"

import {
  FIXED_PRODUCT_LIST_COLUMNS,
  PRODUCT_LIST_OPTIONAL_COLUMNS,
  restoreProductListOptionalColumns,
  updateProductListOptionalColumns,
} from "./productListColumns"

describe("product list columns", () => {
  it("keeps the first three columns fixed and exposes the profit-related fields", () => {
    expect(FIXED_PRODUCT_LIST_COLUMNS).toEqual(["image", "sku", "product_name"])
    expect(PRODUCT_LIST_OPTIONAL_COLUMNS.map(({ key }) => key)).toEqual(expect.arrayContaining([
      "jd_price", "profit", "jd_margin", "gross_margin", "agreement_purchase_price",
    ]))
  })

  it("restores only supported optional columns in saved order", () => {
    expect(restoreProductListOptionalColumns('["image","jd_price","profit","jd_price","unknown"]')).toEqual([
      "jd_price", "profit",
    ])
    expect(restoreProductListOptionalColumns("bad json")).toContain("brand")
  })

  it("uses click order after the three fixed columns", () => {
    const first = updateProductListOptionalColumns([], "jd_price", true)
    const second = updateProductListOptionalColumns(first, "profit", true)
    expect([...FIXED_PRODUCT_LIST_COLUMNS, ...second]).toEqual([
      "image", "sku", "product_name", "jd_price", "profit",
    ])
    expect(updateProductListOptionalColumns(second, "jd_price", false)).toEqual(["profit"])
  })
})
