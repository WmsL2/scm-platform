import { describe, expect, it } from "vitest"
import source from "./BidProjectListView.vue?raw"

describe("BidProjectListView", () => {
  it("gates creation and delegates filtering and pagination to the API", () => {
    expect(source).toContain("auth.hasPermission('bid:create')")
    expect(source).toContain('route.query.action === "create"')
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
  it("supports five independent recommendation types", () => {
    for (const type of [
      "TYPE_1_SPECIFICATION",
      "TYPE_2_IDENTIFIED_PRODUCT",
      "TYPE_3_CATEGORY",
      "TYPE_4_FREE",
      "TYPE_5_PPT",
    ]) expect(source).toContain(`value: "${type}"`)
    expect(source).toContain('projectType: "FREE_RECOMMENDATION"')
    expect(source).toContain('projectType: "PPT_SOLUTION"')
    expect(source).toContain("PPT 方案需求说明不能少于 20 个字符")
    expect(source).not.toContain("客户 PPT 模板")
    expect(source).toContain("自由推品需求说明不能少于 20 个字符")
    expect(source).toContain('["TYPE_3_CATEGORY", "TYPE_4_FREE"].includes(form.recommendation_type) ? recommendationTemplate.value : undefined')
    expect(source).toContain(':show-file-list="false"')
    expect(source).toContain("clearRecommendationTemplate")
    expect(source).toContain('class="filter-form"')
  })

  it("opens Type 1 and Type 2 workbenches without starting matching automatically", () => {
    expect(source).toContain('const isType2 = result.recommendation_type === "TYPE_2_IDENTIFIED_PRODUCT"')
    expect(source).toContain('const isMatchingType = ["TYPE_1_SPECIFICATION", "TYPE_2_IDENTIFIED_PRODUCT"].includes')
    expect(source).not.toContain("bidApi.startMatching(result.id)")
    expect(source).toContain('router.push(`/bid-projects/${result.id}/workbench`)')
    expect(source).toContain("指定商品项目创建成功，请在工作台确认后开始比价")
    expect(source).toContain("规格参数项目创建成功，请在工作台确认后开始匹配")
    expect(source).toContain("row.project_type === 'FILTER_RECOMMENDATION' ? '进入工作台' : '详情'")
  })
})
