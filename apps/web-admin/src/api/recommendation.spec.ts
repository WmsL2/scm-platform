import { afterEach, describe, expect, it, vi } from "vitest"

const http = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn(), post: vi.fn(), postBlob: vi.fn() }))
vi.mock("../shared/http/runtime", () => ({ http }))

describe("recommendation api", () => {
  afterEach(() => Object.values(http).forEach((mock) => mock.mockReset()))

  it("keeps all provisional B contracts in one adapter", async () => {
    http.get.mockResolvedValue({ id: "r1" })
    http.post.mockResolvedValue({ id: "r1" })
    http.patch.mockResolvedValue({ id: "r1" })
    http.postBlob.mockResolvedValue(new Blob(["xlsx"]))
    const { recommendationApi } = await import("./recommendation")

    await recommendationApi.detail("p1")
    await recommendationApi.start("p1")
    await recommendationApi.cancel("r1")
    await recommendationApi.confirm("c1", { selected: true, campaign_price: "100.00" })
    await recommendationApi.export("r1")

    expect(http.get).toHaveBeenCalledWith("/api/v1/recommendations/projects/p1")
    expect(http.post).toHaveBeenNthCalledWith(1, "/api/v1/recommendations/runs", { project_id: "p1" })
    expect(http.post).toHaveBeenNthCalledWith(2, "/api/v1/recommendations/runs/r1/cancel")
    expect(http.patch).toHaveBeenCalledWith("/api/v1/recommendations/candidates/c1/confirmation", { selected: true, campaign_price: "100.00" })
    expect(http.postBlob).toHaveBeenCalledWith("/api/v1/recommendations/runs/r1/export", undefined, { timeoutMs: 300_000 })
  })
})
