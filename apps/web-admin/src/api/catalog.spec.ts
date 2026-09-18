import { afterEach, describe, expect, it, vi } from "vitest"

const http = vi.hoisted(() => ({ get: vi.fn(), getBlob: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }))
vi.mock("../shared/http/runtime", () => ({ http }))

describe("product import api", () => {
  afterEach(() => {
    http.get.mockReset()
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
    await productApi.getImportPreview("task-1")
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
    expect(http.get).toHaveBeenCalledWith("/api/v1/products/imports/task-1")
    expect(http.post).toHaveBeenNthCalledWith(
      2,
      "/api/v1/products/imports/task-1/supplier-matches/match-1/resolve",
      { supplier_id: "supplier-1" },
    )
    expect(http.post).toHaveBeenNthCalledWith(3, "/api/v1/products/imports/task-1/confirm")
    expect(confirmed).toMatchObject({ imported_count: 1 })
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
