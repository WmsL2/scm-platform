import { describe, expect, it } from "vitest"
import source from "./BidProjectListView.vue?raw"

describe("BidProjectListView", () => {
  it("gates creation and delegates filtering and pagination to the API", () => {
    expect(source).toContain("auth.hasPermission('bid:create')")
    expect(source).toContain("bidApi.list({ page: target, page_size: pageSize.value")
    expect(source).toContain("keyword: filters.keyword.trim() || undefined")
    expect(source).toContain("status: filters.status")
    expect(source).toContain('label="匹配处理数"')
  })
  it("validates supported Excel files and presents every import result", () => {
    expect(source).toContain('endsWith(".xlsx")'); expect(source).toContain("25 * 1024 * 1024")
    expect(source).toContain("Excel 未识别到模板，需要完成模板配置")
    expect(source).toContain("Excel 解析失败")
  })
})
