import { describe, expect, it } from "vitest"

import SupplierDetailView from "./SupplierDetailView.vue"

describe("supplier detail cooperation recovery UI contract", () => {
  const source = String(SupplierDetailView.setup)

  it("uses mutually exclusive cooperation commands and their permissions", () => {
    expect(source).toContain('command === "stop" || command === "blacklist"')
    expect(source).toContain('command === "resume"')
    expect(source).toContain('supplier.value.cooperation_status === "STOPPED"')
    expect(source).toContain('supplier.value.cooperation_status === "BLACKLIST"')
    expect(source).toContain('permission: "supplier:resume"')
    expect(source).toContain('permission: "supplier:unblacklist"')
  })

  it("requires a non-blank reason with operation-specific recovery prompts", () => {
    expect(source).toContain("inputPattern: /\\S+/")
    expect(source).toContain('resume: ["\\u8BF7\\u586B')
    expect(source).toContain('unblacklist: ["\\u8BF7\\u586B')
  })
})
