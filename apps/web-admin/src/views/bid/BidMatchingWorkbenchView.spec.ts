import { describe, expect, it } from "vitest"
import source from "./BidMatchingWorkbenchView.vue?raw"

describe("BidMatchingWorkbenchView", () => {
  it("keeps candidates on-demand and renders persisted selection snapshots", () => {
    expect(source).toContain("async function openCandidates(row")
    expect(source).toContain("bidApi.candidates(id, row.id)")
    expect(source).not.toContain("items.map(async")
    expect(source).toContain("product_snapshot"); expect(source).toContain("supplier_snapshot")
    expect(source).toContain("selected_unit_price")
  })
  it("uses candidate selection only and enforces price/no-quote safeguards", () => {
    expect(source).toContain("candidate_id: candidate.value.candidate_id")
    expect(source).not.toContain("product_id:")
    expect(source).toContain("选品单价不能高于需求限价")
    expect(source).toContain("其他原因必须填写说明")
    expect(source).toContain("['UNIQUE_MATCH', 'MULTIPLE_MATCH', 'SELECTED']")
    expect(source).toContain("terminal.value")
  })
  it("renders Type 2 as a read-only automatic lowest-price comparison result", () => {
    expect(source).toContain('recommendation_type === "TYPE_2_IDENTIFIED_PRODUCT"')
    expect(source).toContain("自动选择当前成本价最低且不超过限价的商品")
    expect(source).toContain('v-if="isType1" label="处理"')
    expect(source).toContain("isType2 ? '最低报价' : '选中单价'")
    expect(source).toContain("async function exportResult()")
    expect(source).toContain("导出回填表")
  })

  it("keeps Type 1 and Type 2 inside one direct result flow", () => {
    expect(source).toContain("返回项目列表")
    expect(source).not.toContain("返回项目详情")
    expect(source).toContain("workspace.renameRoute(route.fullPath, workspaceTitle.value)")
    expect(source).toContain("price.value = value.cost_price ?? value.agreement_price ?? \"\"")
  })

  it("waits for explicit user confirmation before starting like Type 4", () => {
    expect(source).toContain("project?.status === 'IMPORTED'")
    expect(source).toContain("客户需求已解析。请确认后点击")
    expect(source).toContain('@click="startMatching"')
    expect(source).not.toContain("onMounted(() => void startMatching())")
  })
})
