import { afterEach, describe, expect, it, vi } from "vitest"

const http = vi.hoisted(() => ({
  get: vi.fn(),
  getBlob: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}))

vi.mock("../shared/http/runtime", () => ({ http }))

describe("supplier api", () => {
  afterEach(() => {
    http.get.mockReset()
    http.getBlob.mockReset()
    http.post.mockReset()
    http.patch.mockReset()
    http.delete.mockReset()
  })

  it("uses delete and two-stage Excel import routes", async () => {
    http.getBlob.mockResolvedValue(new Blob())
    http.post.mockResolvedValue({ id: "batch-1" })
    http.delete.mockResolvedValue({ id: "supplier-1", status: "deleted" })
    const { supplierApi } = await import("./supplier")
    const file = new File(["content"], "suppliers.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    })

    await supplierApi.downloadImportTemplate()
    await supplierApi.previewImport(file)
    await supplierApi.confirmImport("batch-1")
    await supplierApi.delete("supplier-1")

    expect(http.getBlob).toHaveBeenCalledWith("/api/v1/suppliers/imports/template")
    expect(http.post).toHaveBeenNthCalledWith(
      1,
      "/api/v1/suppliers/imports/preview",
      expect.any(FormData),
    )
    expect(http.post).toHaveBeenNthCalledWith(
      2,
      "/api/v1/suppliers/imports/batch-1/confirm",
    )
    expect(http.delete).toHaveBeenCalledWith("/api/v1/suppliers/supplier-1")
  })

  it("uses the frozen paged-list contract", async () => {
    http.get.mockResolvedValue({ items: [], total: 0, page: 2, page_size: 20 })
    const { supplierApi } = await import("./supplier")

    await supplierApi.list({ page: 2, page_size: 20, keyword: "众诚", archive_status: "DRAFT" })

    expect(http.get).toHaveBeenCalledWith(
      "/api/v1/suppliers?page=2&page_size=20&keyword=%E4%BC%97%E8%AF%9A&archive_status=DRAFT",
    )
  })

  it("uses create, update and lifecycle command routes", async () => {
    http.post.mockResolvedValue({ id: "supplier-1" })
    http.patch.mockResolvedValue({ id: "supplier-1" })
    const { supplierApi } = await import("./supplier")
    const payload = {
      supplier_name: "众诚供应商",
      main_brands: "品牌 A",
      advantage: "服务",
      contacts: [],
    }

    await supplierApi.create(payload)
    await supplierApi.update("supplier-1", payload)
    await supplierApi.command("supplier-1", "stop", "合作终止")
    await supplierApi.command("supplier-1", "submit")

    expect(http.post).toHaveBeenNthCalledWith(1, "/api/v1/suppliers", payload)
    expect(http.patch).toHaveBeenCalledWith("/api/v1/suppliers/supplier-1", payload)
    expect(http.post).toHaveBeenNthCalledWith(
      2,
      "/api/v1/suppliers/supplier-1/commands/stop",
      { reason: "合作终止" },
    )
    expect(http.post).toHaveBeenNthCalledWith(
      3,
      "/api/v1/suppliers/supplier-1/commands/submit",
      undefined,
    )
  })
})
