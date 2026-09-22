import { describe, expect, it } from "vitest"

import { clearSupplierSelection, isAllSuppliersSelected, mergeSupplierPageSelection } from "./supplierExportSelection"
import supplierListSource from "./SupplierListView.vue?raw"

describe("supplier export selection", () => {
  it("keeps page-one selections while changing page-two selection", () => {
    let selected = mergeSupplierPageSelection(new Set(), ["a", "b"], ["a", "b"])
    selected = mergeSupplierPageSelection(selected, ["c", "d"], ["c"])
    selected = mergeSupplierPageSelection(selected, ["c", "d"], ["d"])
    expect([...selected].sort()).toEqual(["a", "b", "d"])
  })

  it("recognizes and clears all filtered selections", () => {
    expect(isAllSuppliersSelected(new Set(), 0)).toBe(false)
    expect(isAllSuppliersSelected(new Set(["a", "b"]), 2)).toBe(true)
    expect(isAllSuppliersSelected(new Set(["a"]), 2)).toBe(false)
    expect(clearSupplierSelection()).toEqual(new Set())
  })

  it("wires selection, selected export, and filter reset into the supplier page", () => {
    expect(supplierListSource).toContain('type="selection"')
    expect(supplierListSource).toContain('@selection-change="syncSelection"')
    expect(supplierListSource).toContain("supplierApi.getSelectionIds(supplierFilterParams())")
    expect(supplierListSource).toContain("supplierApi.exportSelected([...selectedSupplierIds.value])")
    expect(supplierListSource).toContain("导出 Excel（{{ selectedSupplierIds.size }}）")
    expect(supplierListSource).toContain("selectedSupplierIds.value.clear()")
  })
})
