import { afterEach, describe, expect, it, vi } from "vitest"

const http = vi.hoisted(() => ({ get: vi.fn(), getBlob: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }))
vi.mock("../shared/http/runtime", () => ({ http }))

describe("product import api", () => {
  afterEach(() => {
    http.get.mockReset()
    http.getBlob.mockReset()
    http.post.mockReset()
    http.patch.mockReset()
    http.delete.mockReset()
  })

  it("uses preview, template, candidate, resolve and confirm Product Import routes", async () => {
    http.post
      .mockResolvedValueOnce({ id: "task-1" })
      .mockResolvedValueOnce({ id: "task-1" })
      .mockResolvedValueOnce({ id: "task-1", status: "CONFIRMED", imported_count: 1 })
    http.get.mockResolvedValue([])
    http.getBlob.mockResolvedValue(new Blob(["template"]))
    const { productApi } = await import("./catalog")
    const file = new File(["content"], "products.xlsx")

    await productApi.previewImport(file)
    await productApi.downloadImportTemplate()
    await productApi.exportFailedImportRows("task-1")
    await productApi.getImportPreview("task-1", {
      page: 1,
      page_size: 50,
      row_status: "ALL",
    })
    await productApi.importSupplierCandidates()
    await productApi.resolveImportSupplier("task-1", "match-1", "supplier-1")
    const confirmed = await productApi.confirmImport("task-1")

    expect(http.post).toHaveBeenNthCalledWith(
      1,
      "/api/v1/products/imports/preview",
      expect.any(FormData),
      { timeoutMs: 900_000 },
    )
    expect(http.get).toHaveBeenCalledWith("/api/v1/products/imports/supplier-candidates")
    expect(http.getBlob).toHaveBeenCalledWith("/api/v1/products/imports/template")
    expect(http.getBlob).toHaveBeenCalledWith(
      "/api/v1/products/imports/task-1/failed-rows",
      { timeoutMs: 900_000 },
    )
    expect(http.get).toHaveBeenCalledWith(
      "/api/v1/products/imports/task-1?page=1&page_size=50&row_status=ALL",
    )
    expect(http.post).toHaveBeenNthCalledWith(
      2,
      "/api/v1/products/imports/task-1/supplier-matches/match-1/resolve",
      { supplier_id: "supplier-1" },
    )
    expect(http.post).toHaveBeenNthCalledWith(
      3,
      "/api/v1/products/imports/task-1/confirm",
      undefined,
      { timeoutMs: 900_000 },
    )
    expect(confirmed).toMatchObject({ imported_count: 1 })
  })

  it("discards a closed import preview and its temporary workbook", async () => {
    http.post.mockResolvedValue({ id: "task-1", status: "EXPIRED" })
    const { productApi } = await import("./catalog")

    await productApi.discardImport("task-1")

    expect(http.post).toHaveBeenCalledWith(
      "/api/v1/products/imports/task-1/discard",
    )
  })

  it("passes the related supplier filter to the product list API", async () => {
    http.get.mockResolvedValue({ items: [] })
    const { productApi } = await import("./catalog")

    await productApi.list({ source_supplier_id: "supplier-1", page: 1, page_size: 20 })

    expect(http.get).toHaveBeenCalledWith(
      "/api/v1/products?source_supplier_id=supplier-1&page=1&page_size=20",
    )
  })

  it("repeats each selected category ID in the product list query", async () => {
    http.get.mockResolvedValue({ items: [] })
    const { productApi } = await import("./catalog")

    await productApi.list({ category_selections: ["LEVEL1:test-a", "LEVEL2:test-b"] })

    expect(http.get).toHaveBeenCalledWith(
      "/api/v1/products?category_selections=LEVEL1%3Atest-a&category_selections=LEVEL2%3Atest-b",
    )
  })

  it("repeats each direct category selection in the product list query", async () => {
    http.get.mockResolvedValue({ items: [] })
    const { productApi } = await import("./catalog")

    await productApi.list({
      category_selections: ["LEVEL1:category-1", "LEVEL3:category-2"],
    })

    expect(http.get).toHaveBeenCalledWith(
      "/api/v1/products?category_selections=LEVEL1%3Acategory-1&category_selections=LEVEL3%3Acategory-2",
    )
  })

  it("uses the same filter serializer for selection IDs", async () => {
    http.get.mockResolvedValue({ ids: ["product-1"], total: 1 })
    const { productApi } = await import("./catalog")

    await productApi.getSelectionIds({
      keyword: "打印纸",
      brand: "测试品牌",
      company_names: ["众诚公司"],
      purchasing_agents: ["张三"],
      brands: ["品牌 A"],
      source_supplier_ids: ["supplier-1"],
      jd_price_min: "100",
      jd_price_max: "200",
      profit_min: "-5",
      profit_max: "30",
      status: "DISABLED",
      category_selections: ["LEVEL1:office"],
    })

    expect(http.get).toHaveBeenCalledWith(
      "/api/v1/products/selection-ids?keyword=%E6%89%93%E5%8D%B0%E7%BA%B8&brand=%E6%B5%8B%E8%AF%95%E5%93%81%E7%89%8C&company_names=%E4%BC%97%E8%AF%9A%E5%85%AC%E5%8F%B8&purchasing_agents=%E5%BC%A0%E4%B8%89&brands=%E5%93%81%E7%89%8C+A&source_supplier_ids=supplier-1&jd_price_min=100&jd_price_max=200&profit_min=-5&profit_max=30&status=DISABLED&category_selections=LEVEL1%3Aoffice",
    )
  })

  it("repeats multi-select product filters and sends JD price and profit ranges", async () => {
    http.get.mockResolvedValue({ items: [] })
    const { productApi } = await import("./catalog")

    await productApi.list({
      company_names: ["众诚公司"],
      purchasing_agents: ["张三", "李四"],
      brands: ["品牌 A", "品牌 B"],
      source_supplier_ids: ["supplier-1", "supplier-2"],
      jd_price_min: "100",
      jd_price_max: "200",
      profit_min: "-5",
      profit_max: "30",
    })

    expect(http.get).toHaveBeenCalledWith(
      "/api/v1/products?company_names=%E4%BC%97%E8%AF%9A%E5%85%AC%E5%8F%B8&purchasing_agents=%E5%BC%A0%E4%B8%89&purchasing_agents=%E6%9D%8E%E5%9B%9B&brands=%E5%93%81%E7%89%8C+A&brands=%E5%93%81%E7%89%8C+B&source_supplier_ids=supplier-1&source_supplier_ids=supplier-2&jd_price_min=100&jd_price_max=200&profit_min=-5&profit_max=30",
    )
  })

  it("loads remote Product filter options", async () => {
    http.get.mockResolvedValue({ items: [], has_more: false })
    const { productApi } = await import("./catalog")

    await productApi.filterOptions("SUPPLIER", "众诚", 50, "DISABLED")

    expect(http.get).toHaveBeenCalledWith(
      "/api/v1/products/filter-options?field=SUPPLIER&limit=50&offset=50&status=DISABLED&keyword=%E4%BC%97%E8%AF%9A",
    )
  })

  it("loads Product Master category filter options with the active filter context", async () => {
    http.get.mockResolvedValue({ items: [], has_more: false })
    const { productApi } = await import("./catalog")

    await productApi.categoryFilterOptions(
      "LEVEL3",
      "相机",
      50,
      ["LEVEL1:token"],
      "DISABLED",
    )

    expect(http.get).toHaveBeenCalledWith(
      "/api/v1/products/category-filter-options?level=LEVEL3&limit=50&offset=50&status=DISABLED&keyword=%E7%9B%B8%E6%9C%BA&category_selections=LEVEL1%3Atoken",
    )
  })

  it("uses product lifecycle routes", async () => {
    http.post.mockResolvedValue({ id: "product-1", status: "DISABLED" })
    http.delete.mockResolvedValue({ id: "product-1", status: "PURGED" })
    const { productApi } = await import("./catalog")

    await productApi.disable("product-1")
    await productApi.enable("product-1")
    await productApi.purge("product-1")

    expect(http.post).toHaveBeenNthCalledWith(1, "/api/v1/products/product-1/commands/disable")
    expect(http.post).toHaveBeenNthCalledWith(2, "/api/v1/products/product-1/commands/enable")
    expect(http.delete).toHaveBeenCalledWith("/api/v1/products/product-1", { confirm: true })
  })

  it("uses controlled product image routes", async () => {
    http.post.mockResolvedValue({ id: "product-1" })
    http.delete.mockResolvedValue({ id: "product-1", image_reference: null })
    const { productApi } = await import("./catalog")
    const image = new File(["image"], "product.png", { type: "image/png" })

    await productApi.updateImage("product-1", image)
    await productApi.clearImage("product-1")

    expect(http.post).toHaveBeenCalledWith(
      "/api/v1/products/product-1/image",
      expect.any(FormData),
    )
    expect(http.delete).toHaveBeenCalledWith("/api/v1/products/product-1/image")
  })
})
