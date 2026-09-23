import { describe, expect, it } from "vitest"
import source from "./RecommendationWorkspaceView.vue?raw"

describe("RecommendationWorkspaceView", () => {
  it("requires confirmed template mapping before starting or exporting", () => {
    expect(source).toContain("mappingConfirmed")
    expect(source).toContain("请先确认模板字段映射")
    expect(source).toContain("run.value?.status === \"CONFIRMED\"")
    expect(source).toContain("recommendation:export")
  })

  it("shows controlled Agent progress and human confirmation", () => {
    expect(source).toContain("Agent 运行状态")
    expect(source).toContain("需求理解")
    expect(source).toContain("推荐类目方向")
    expect(source).toContain("候选商品与人工确认")
    expect(source).toContain("Agent 只提供排序建议")
    expect(source).toContain("人工确认已保存")
  })
})
