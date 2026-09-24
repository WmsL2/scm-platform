import { describe, expect, it } from "vitest"
import source from "./BidProjectListView.vue?raw"

describe("BidProjectListView", () => {
  it("gates creation and delegates filtering and pagination to the API", () => {
    expect(source).toContain("auth.hasPermission('bid:create')")
    expect(source).toContain("const result = await bidApi.list({")
    expect(source).toContain("page: target")
    expect(source).toContain("page_size: pageSize.value")
    expect(source).toContain("keyword: filters.keyword.trim() || undefined")
    expect(source).toContain("status: filters.status")
    expect(source).toContain('label="匹配处理数"')
  })
  it("validates supported Excel files and presents every import result", () => {
    expect(source).toContain('endsWith(".xlsx")'); expect(source).toContain("25 * 1024 * 1024")
    expect(source).toContain("Excel 未识别到模板，需要完成模板配置")
    expect(source).toContain("Excel 解析失败")
  })
  it("supports type 4 creation and keeps type 5 closed", () => {
    expect(source).toContain('value: "FREE_RECOMMENDATION"')
    expect(source).toContain('value: "PPT_SOLUTION"')
    expect(source).toContain('disabled: true')
    expect(source).toContain("自由推品需求说明不能少于 20 个字符")
    expect(source).toContain("recommendation_template: recommendationTemplate.value")
    expect(source).toContain(':show-file-list="false"')
    expect(source).toContain("clearRecommendationTemplate")
    expect(source).toContain('class="filter-form"')
  })
})
