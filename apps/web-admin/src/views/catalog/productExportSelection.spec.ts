import { describe, expect, it } from "vitest"
import productListSource from "./ProductListView.vue?raw"
import { PRODUCT_EXPORT_COLUMN_DEFINITIONS, PRODUCT_EXPORT_COLUMNS } from "../../types/catalog"
import {
  clearProductSelection,
  isAllProductsSelected,
  mergePageSelection,
  restoreExportColumns,
} from "./productExportSelection"

describe("product export selection", () => {
  it("confirms when the selected-product workbook starts downloading", () => {
    expect(productListSource).toContain('ElMessage.success("商品导出成功，文件已开始下载")')
    expect(productListSource.indexOf('ElMessage.success("商品导出成功，文件已开始下载")'))
      .toBeGreaterThan(productListSource.indexOf("await productApi.exportSelected("))
  })
  it("restores only valid fields and falls back to all 43", () => {
    expect(restoreExportColumns(null)).toHaveLength(43)
    expect(restoreExportColumns('["sku","product_name","cost_price"]')).toEqual(["sku", "product_name", "cost_price"])
    expect(restoreExportColumns('["sku","bad"]')).toEqual(["sku"])
    expect(restoreExportColumns("[]")).toEqual(PRODUCT_EXPORT_COLUMNS)
    expect(restoreExportColumns("bad json")).toEqual(PRODUCT_EXPORT_COLUMNS)
    expect(restoreExportColumns('["company_name","所属公司"]')).toEqual(["company_name"])
  })
  it("defines the canonical 43 export fields with Chinese labels", () => {
    expect(PRODUCT_EXPORT_COLUMN_DEFINITIONS).toHaveLength(43)
    expect(PRODUCT_EXPORT_COLUMNS).toEqual([
      "company_name", "listed_at", "brand", "image_reference", "model", "sku", "product_name", "category_level1_name", "category_level2_name", "category_level3_name", "item_number", "jd_same_product_url", "cost_price", "market_price", "jd_price", "agreement_price", "agreement_purchase_price", "profit", "jd_margin", "deduction_review", "gross_margin", "purchasing_agent", "supplier_name", "barcode_text", "certification_3c_code", "product_specification", "selling_points", "packaging_list", "warranty_period", "restricted_regions", "jd_self_operated_price", "storefront_type", "reference_url", "sales_volume", "positive_rating", "discount_rate", "price_inflation_rate", "tax_code", "invoice_name", "tax_category", "shipping_courier", "after_sales_policy", "remark",
    ])
    const labels = new Map(PRODUCT_EXPORT_COLUMN_DEFINITIONS.map(({ key, label }) => [key, label]))
    expect(labels.get("company_name")).toBe("所属公司")
    expect(labels.get("image_reference")).toBe("图片")
    expect(labels.get("supplier_name")).toBe("供应商")
    expect(labels.get("after_sales_policy")).toBe("售后政策")
  })
  it("preserves other-page selections and removes only current-page deselection", () => {
    const first = mergePageSelection(new Set(), ["A", "B"], ["A"])
    const second = mergePageSelection(first, ["C", "D"], ["C"])
    expect([...second]).toEqual(["A", "C"])
    expect([...mergePageSelection(second, ["A", "B"], [])]).toEqual(["C"])
  })

  it("keeps other selections when a selected-all current page is partially deselected", () => {
    expect(
      [...mergePageSelection(new Set(["A", "B", "C", "D"]), ["A", "B"], ["B"])],
    ).toEqual(["B", "C", "D"])
  })

  it("merges a newly checked current-page row without dropping prior pages", () => {
    expect(
      [...mergePageSelection(new Set(["A", "C"]), ["C", "D"], ["C", "D"])],
    ).toEqual(["A", "C", "D"])
  })

  it("identifies every selected product without a separate all-selected state", () => {
    expect(isAllProductsSelected(new Set(["A", "B", "C", "D"]), 4)).toBe(true)
    expect(isAllProductsSelected(new Set(["A", "B", "C"]), 4)).toBe(false)
    expect(isAllProductsSelected(new Set(), 0)).toBe(false)
    expect([...clearProductSelection()]).toEqual([])
  })

  it("selects all export fields in canonical order", () => {
    expect([...PRODUCT_EXPORT_COLUMNS]).toHaveLength(43)
    expect([...PRODUCT_EXPORT_COLUMNS]).toEqual(PRODUCT_EXPORT_COLUMNS)
  })
})
