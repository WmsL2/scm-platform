import { describe, expect, it } from "vitest"

import {
  commandRequiresReason,
  createSupplierFormDraft,
  normalizeSupplierDraft,
  supplierDraftValidationMessage,
} from "./supplier"

describe("supplier frontend boundary", () => {
  it("creates a draft with only frozen editable fields", () => {
    expect(createSupplierFormDraft()).toEqual({
      supplier_name: "",
      main_brands: "",
      advantage: "",
      archive_status: "DRAFT",
      contacts: [],
    })
  })

  it("requires a reason only for stop and blacklist commands", () => {
    expect(commandRequiresReason("submit")).toBe(false)
    expect(commandRequiresReason("archive")).toBe(false)
    expect(commandRequiresReason("stop")).toBe(true)
    expect(commandRequiresReason("blacklist")).toBe(true)
  })

  it("normalizes optional contacts and requires all frozen main fields", () => {
    const draft = normalizeSupplierDraft({
      supplier_name: " 众诚供应商 ",
      main_brands: " 品牌 A ",
      advantage: " 服务 ",
      archive_status: "DRAFT",
      contacts: [
        { contact_name: " 李四 ", contact_phone: " 13800000000 " },
        { contact_name: " ", contact_phone: " " },
      ],
    })
    expect(draft).toEqual({
      supplier_name: "众诚供应商",
      main_brands: "品牌 A",
      advantage: "服务",
      archive_status: "DRAFT",
      contacts: [{ contact_name: "李四", contact_phone: "13800000000" }],
    })
    expect(supplierDraftValidationMessage(createSupplierFormDraft())).toBe("请填写供应商名称")
  })
})
