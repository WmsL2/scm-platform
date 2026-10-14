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
    expect(source).toContain("查看全部匹配")
    expect(source).toContain("terminal.value")
  })
  it("renders Type 2 as a read-only AI-assisted exact-first comparison result", () => {
    expect(source).toContain('recommendation_type === "TYPE_2_IDENTIFIED_PRODUCT"')
    expect(source).toContain("品牌+型号召回")
    expect(source).toContain("同类型替代")
    expect(source).toContain("row.current_selection?.note")
    expect(source).toContain('v-if="isType1" label="处理"')
    expect(source).toContain("isType2 ? '最低协议价' : '协议价'")
    expect(source).toContain("async function exportResult()")
    expect(source).toContain("导出回填表")
  })

  it("keeps Type 1 and Type 2 inside one direct result flow", () => {
    expect(source).toContain("返回项目列表")
    expect(source).not.toContain("返回项目详情")
    expect(source).toContain("workspace.renameRoute(route.fullPath, workspaceTitle.value)")
    expect(source).toContain("price.value = value.agreement_price ?? \"\"")
    expect(source).toContain('prop="agreement_price" label="协议价"')
  })

  it("waits for explicit user confirmation before starting like Type 4", () => {
    expect(source).toContain("project?.status === 'IMPORTED'")
    expect(source).toContain('["SELECTING", "READY"].includes(status)')
    expect(source).toContain("全部命中商品将逐行导出")
    expect(source).toContain("客户需求和回填字段已确认。请点击")
    expect(source).toContain('@click="startMatching"')
    expect(source).not.toContain("onMounted(() => void startMatching())")
  })

  it("reviews AI-prefilled output columns without changing matching inputs", () => {
    expect(source).toContain("bidApi.outputMapping(id)")
    expect(source).toContain("bidApi.updateOutputMapping")
    expect(source).toContain("客户原表回填字段")
    expect(source).toContain("客户原表列（不可修改）")
    expect(source).toContain("商品主数据／报价结果字段（可搜索选择）")
    expect(source).toContain("outputMappingSelections[header]")
    expect(source).toContain("outputMapping.value.suggested_headers")
    expect(source).toContain('v-for="(header, index) in outputMappingHeaders"')
    expect(source).toContain("从本次上传模板补充待回填列")
    expect(source).toContain("addOutputHeader")
    expect(source).toContain(':disabled="outputMappingHeaders.includes(header)"')
    expect(source).not.toContain('v-for="(header, index) in outputMapping.headers"')
    expect(source).toContain("Object.hasOwn(outputMappingSelections, header)")
    expect(source).toContain("Object.fromEntries")
    expect(source).toContain('class="output-mapping-row"')
    expect(source).toContain("不会改变商品匹配条件")
    expect(source).toContain("outputMapping.value?.confirmed === true")
    expect(source).not.toContain("请选择商品报价（单价）的回填列")
  })
})
