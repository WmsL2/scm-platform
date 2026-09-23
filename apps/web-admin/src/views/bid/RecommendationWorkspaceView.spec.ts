import { describe, expect, it } from "vitest"
import source from "./RecommendationWorkspaceView.vue?raw"

describe("RecommendationWorkspaceView", () => {
  it("requires confirmed template mapping and confirmed candidates before exporting", () => {
    expect(source).toContain("mappingConfirmed")
    expect(source).toContain("请先确认模板字段映射")
    expect(source).toContain("recommendation:export")
    expect(source).toContain("exportConfirmedCandidates")
    expect(source).toContain("recommendationApi.downloadExport")
  })

  it("shows controlled Agent progress and human confirmation", () => {
    expect(source).toContain("Agent 运行状态")
    expect(source).toContain("需求理解")
    expect(source).toContain("推荐类目方向")
    expect(source).toContain("候选商品与人工确认")
    expect(source).toContain("Agent 只提供排序建议")
    expect(source).toContain("人工确认已保存")
    expect(source).toContain("批量确认选中")
    expect(source).toContain("recommendationApi.confirmMany")
    expect(source).toContain("recommendationApi.run(runId)")
    expect(source).toContain("runHistory")
  })
  it("shows the exact requirement snapshot and can resume after supplemental input", () => {
    expect(source).toContain("本次 Agent 实际读取的需求")
    expect(source).toContain("run.raw_requirement_snapshot")
    expect(source).toContain("保存补充说明并重新生成")
    expect(source).toContain("bidApi.update(projectId")
  })
})
