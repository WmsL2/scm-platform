import { describe, expect, it } from "vitest"
import source from "./BidMatchingWorkbenchView.vue?raw"

describe("BidMatchingWorkbenchView", () => {
  it("keeps candidates on-demand and renders persisted selection snapshots", () => {
    expect(source).toContain("async function openCandidates(row")
    expect(source).toContain("bidApi.candidates(id,row.id)")
    expect(source).not.toContain("items.map(async")
    expect(source).toContain("product_snapshot"); expect(source).toContain("supplier_snapshot")
    expect(source).toContain("selected_unit_price")
  })
  it("uses candidate selection only and enforces price/no-quote safeguards", () => {
    expect(source).toContain("candidate_id:candidate.value.candidate_id")
    expect(source).not.toContain("product_id:")
    expect(source).toContain("选品单价不能高于需求限价")
    expect(source).toContain("其他原因必须填写说明")
    expect(source).toContain("['NO_MATCH','UNIQUE_MATCH','MULTIPLE_MATCH','SELECTED']")
    expect(source).toContain("terminal()")
  })
})
