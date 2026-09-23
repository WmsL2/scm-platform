import { afterEach, describe, expect, it, vi } from "vitest"

const http = vi.hoisted(() => ({ get: vi.fn(), getBlob: vi.fn(), patch: vi.fn(), post: vi.fn() }))
vi.mock("../shared/http/runtime", () => ({ http }))

describe("bid api", () => {
  afterEach(() => Object.values(http).forEach((mock) => mock.mockReset()))

  it("uses all project read routes with only populated query values", async () => {
    http.get.mockResolvedValue({ items: [] }); http.getBlob.mockResolvedValue(new Blob(["file"]))
    const { bidApi } = await import("./bid")
    await bidApi.list({ page: 2, page_size: 50, keyword: " project ", status: "SELECTING" })
    await bidApi.get("p1"); await bidApi.items("p1", { page: 3, page_size: 20, keyword: "model", status: "MULTIPLE_MATCH" })
    await bidApi.files("p1"); await bidApi.download("p1", "f1"); await bidApi.candidates("p1", "i1")
    expect(http.get).toHaveBeenNthCalledWith(1, "/api/v1/bid-projects?page=2&page_size=50&keyword=+project+&status=SELECTING")
    expect(http.get).toHaveBeenNthCalledWith(2, "/api/v1/bid-projects/p1")
    expect(http.get).toHaveBeenNthCalledWith(3, "/api/v1/bid-projects/p1/items?page=3&page_size=20&keyword=model&status=MULTIPLE_MATCH")
    expect(http.get).toHaveBeenNthCalledWith(4, "/api/v1/bid-projects/p1/files")
    expect(http.getBlob).toHaveBeenCalledWith("/api/v1/bid-projects/p1/files/f1/download")
    expect(http.get).toHaveBeenNthCalledWith(5, "/api/v1/bid-projects/p1/items/i1/candidates")
  })

  it("uses multipart create and long timeouts for every inline long operation", async () => {
    http.post.mockResolvedValue({ id: "p1" })
    const { bidApi } = await import("./bid")
    await bidApi.create({ project_type: "FILTER_RECOMMENDATION", file: new File(["xlsx"], "request.xlsx"), project_name: "项目", buyer_name: "需求商", deadline_at: "2026-09-20T10:00:00", remark: "备注" })
    await bidApi.startMatching("p1"); await bidApi.export("p1")
    const form = http.post.mock.calls[0][1] as FormData
    expect(http.post.mock.calls[0][0]).toBe("/api/v1/bid-projects")
    expect(form.get("file")).toBeInstanceOf(File); expect(form.get("project_type")).toBe("FILTER_RECOMMENDATION"); expect(form.get("project_name")).toBe("项目"); expect(form.get("buyer_name")).toBe("需求商")
    expect(http.post.mock.calls[0][2]).toEqual({ timeoutMs: 300_000 })
    expect(http.post).toHaveBeenNthCalledWith(2, "/api/v1/bid-projects/p1/commands/start-matching", undefined, { timeoutMs: 300_000 })
    expect(http.post).toHaveBeenNthCalledWith(3, "/api/v1/bid-projects/p1/exports", undefined, { timeoutMs: 300_000 })
  })

  it("uses candidate-only selection and lifecycle command payloads", async () => {
    http.post.mockResolvedValue({})
    const { bidApi } = await import("./bid")
    await bidApi.select("p1", "i1", { candidate_id: "c2", selected_unit_price: "10.25", note: "确认" })
    await bidApi.noQuote("p1", "i1", { reason: "OTHER", reason_detail: "无法供货" })
    await bidApi.submit("p1", { submitted_file_id: "f2", note: "已提交" }); await bidApi.win("p1", "中标"); await bidApi.lose("p1")
    expect(http.post).toHaveBeenNthCalledWith(1, "/api/v1/bid-projects/p1/items/i1/selections", { candidate_id: "c2", selected_unit_price: "10.25", note: "确认" })
    expect(http.post.mock.calls[0][1]).not.toHaveProperty("product_id")
    expect(http.post).toHaveBeenNthCalledWith(2, "/api/v1/bid-projects/p1/items/i1/no-quote", { reason: "OTHER", reason_detail: "无法供货" })
    expect(http.post).toHaveBeenNthCalledWith(3, "/api/v1/bid-projects/p1/commands/submit", { submitted_file_id: "f2", note: "已提交" })
    expect(http.post).toHaveBeenNthCalledWith(4, "/api/v1/bid-projects/p1/commands/win", { note: "中标" })
    expect(http.post).toHaveBeenNthCalledWith(5, "/api/v1/bid-projects/p1/commands/lose", undefined)
  })

  it("updates basic information and voids a project through their dedicated routes", async () => {
    http.patch.mockResolvedValue({}); http.post.mockResolvedValue({})
    const { bidApi } = await import("./bid")
    await bidApi.update("p1", { project_name: "项目", buyer_name: "需求商", start_at: null, deadline_at: "2026-09-20T10:00:00", remark: null })
    await bidApi.voidProject("p1", { reason: "业务取消" })
    expect(http.patch).toHaveBeenCalledWith("/api/v1/bid-projects/p1", { project_name: "项目", buyer_name: "需求商", start_at: null, deadline_at: "2026-09-20T10:00:00", remark: null })
    expect(http.post).toHaveBeenCalledWith("/api/v1/bid-projects/p1/commands/void", { reason: "业务取消" })
  })
})
