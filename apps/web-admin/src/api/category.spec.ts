import { afterEach, describe, expect, it, vi } from "vitest"

const http = vi.hoisted(() => ({ get: vi.fn(), getBlob: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))
vi.mock("../shared/http/runtime", () => ({ http }))

describe("category api", () => {
  afterEach(() => Object.values(http).forEach((mock) => mock.mockReset()))

  it("uses Category CRUD, bounded filter options, selection, template and import endpoints", async () => {
    http.get.mockResolvedValue([]); http.post.mockResolvedValue({ id: "category-1" }); http.put.mockResolvedValue({ id: "category-1" }); http.delete.mockResolvedValue(undefined); http.getBlob.mockResolvedValue(new Blob(["template"]))
    const { categoryApi } = await import("./category")
    const item = { source_type: "MALL_LEVEL3" as const, level1_name: "一", level2_name: "二", level3_name: "三", level1_external_id: "1", level2_external_id: "2", level3_external_id: "3", deduction_rate: "0.0800", is_active: true, shelf_flag: null, business_unit: null }
    await categoryApi.selection()
    await categoryApi.filterOptions("LEVEL3", "相机", 50)
    await categoryApi.list()
    await categoryApi.list({ page: 1, page_size: 20, level1_name: "个人护理", level2_name: "假发", level3_name: "假发配件", deduction_rate: "0.05", is_active: false, business_unit: "京东零售" })
    await categoryApi.create(item); await categoryApi.update("category-1", item); await categoryApi.remove("category-1"); await categoryApi.template(); await categoryApi.import(new File(["xlsx"], "categories.xlsx"), "5")
    expect(http.get).toHaveBeenCalledWith("/api/v1/categories?page=1&page_size=20")
    expect(http.get).toHaveBeenCalledWith("/api/v1/categories/selection")
    expect(http.get).toHaveBeenCalledWith("/api/v1/categories/filter-options?level=LEVEL3&limit=50&offset=50&keyword=%E7%9B%B8%E6%9C%BA")
    expect(http.get).toHaveBeenCalledWith("/api/v1/categories?page=1&page_size=20&level1_name=%E4%B8%AA%E4%BA%BA%E6%8A%A4%E7%90%86&level2_name=%E5%81%87%E5%8F%91&level3_name=%E5%81%87%E5%8F%91%E9%85%8D%E4%BB%B6&deduction_rate=0.05&is_active=false&business_unit=%E4%BA%AC%E4%B8%9C%E9%9B%B6%E5%94%AE")
    expect(http.post).toHaveBeenNthCalledWith(1, "/api/v1/categories", item)
    expect(http.put).toHaveBeenCalledWith("/api/v1/categories/category-1", item)
    expect(http.delete).toHaveBeenCalledWith("/api/v1/categories/category-1")
    expect(http.getBlob).toHaveBeenCalledWith("/api/v1/categories/imports/template")
    expect(http.post).toHaveBeenNthCalledWith(2, "/api/v1/categories/imports", expect.any(FormData))
    const importBody = http.post.mock.calls[1][1] as FormData
    expect(importBody.get("file")).toBeInstanceOf(File)
    expect(importBody.get("deduction_rate_percent")).toBe("5")
    expect(importBody.has("source_type")).toBe(false)
    expect(importBody.has("deduction_rate")).toBe(false)
  })
})
