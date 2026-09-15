import { afterEach, describe, expect, it, vi } from "vitest"

const http = vi.hoisted(() => ({ get: vi.fn(), getBlob: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))
vi.mock("../shared/http/runtime", () => ({ http }))

describe("category api", () => {
  afterEach(() => Object.values(http).forEach((mock) => mock.mockReset()))

  it("uses Category CRUD, selection, template and import endpoints", async () => {
    http.get.mockResolvedValue([]); http.post.mockResolvedValue({ id: "category-1" }); http.put.mockResolvedValue({ id: "category-1" }); http.delete.mockResolvedValue(undefined); http.getBlob.mockResolvedValue(new Blob(["template"]))
    const { categoryApi } = await import("./category")
    const item = { source_type: "MALL_LEVEL3" as const, level1_name: "一", level2_name: "二", level3_name: "三", level1_external_id: "1", level2_external_id: "2", level3_external_id: "3", deduction_rate: "0.0800", is_active: true, shelf_flag: null, business_unit: null }
    await categoryApi.list(); await categoryApi.list(true); await categoryApi.create(item); await categoryApi.update("category-1", item); await categoryApi.remove("category-1"); await categoryApi.template(); await categoryApi.import(new File(["xlsx"], "categories.xlsx"))
    expect(http.get).toHaveBeenCalledWith("/api/v1/categories")
    expect(http.get).toHaveBeenCalledWith("/api/v1/categories?active_only=true")
    expect(http.post).toHaveBeenNthCalledWith(1, "/api/v1/categories", item)
    expect(http.put).toHaveBeenCalledWith("/api/v1/categories/category-1", item)
    expect(http.delete).toHaveBeenCalledWith("/api/v1/categories/category-1")
    expect(http.getBlob).toHaveBeenCalledWith("/api/v1/categories/imports/template")
    expect(http.post).toHaveBeenNthCalledWith(2, "/api/v1/categories/imports", expect.any(FormData))
  })
})
