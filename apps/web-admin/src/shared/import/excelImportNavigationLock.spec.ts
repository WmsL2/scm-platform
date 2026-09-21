import { describe, expect, it, vi } from "vitest"

import {
  canLeaveExcelImport,
  protectExcelImportBeforeUnload,
} from "./excelImportNavigationLock"
import bidProjectListSource from "../../views/bid/BidProjectListView.vue?raw"
import categoryListSource from "../../views/catalog/CategoryListView.vue?raw"
import productListSource from "../../views/catalog/ProductListView.vue?raw"
import supplierListSource from "../../views/supplier/SupplierListView.vue?raw"

describe("Excel import navigation lock", () => {
  it("allows navigation and unload when no import is running", () => {
    const event = {
      preventDefault: vi.fn(),
      returnValue: undefined,
    } as unknown as BeforeUnloadEvent

    expect(canLeaveExcelImport(false)).toBe(true)
    expect(protectExcelImportBeforeUnload(event, false)).toBe(false)
    expect(event.preventDefault).not.toHaveBeenCalled()
  })

  it("blocks navigation and requests a browser warning while importing", () => {
    const event = {
      preventDefault: vi.fn(),
      returnValue: undefined,
    } as unknown as BeforeUnloadEvent

    expect(canLeaveExcelImport(true)).toBe(false)
    expect(protectExcelImportBeforeUnload(event, true)).toBe(true)
    expect(event.preventDefault).toHaveBeenCalledOnce()
    expect(event.returnValue).toBe("")
  })

  it("is wired into every current Excel import view", () => {
    const importViews = [
      productListSource,
      supplierListSource,
      categoryListSource,
      bidProjectListSource,
    ]

    expect(importViews).toHaveLength(4)
    for (const source of importViews) {
      expect(source).toContain("useExcelImportNavigationLock")
      expect(source).toContain("importNavigationLock.start()")
      expect(source).toContain("importNavigationLock.stop()")
    }
  })
})
