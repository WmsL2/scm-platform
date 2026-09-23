import { afterEach, describe, expect, it, vi } from "vitest"

const http = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn(), post: vi.fn() }))
vi.mock("../shared/http/runtime", () => ({ http }))

describe("recommendation api", () => {
  afterEach(() => Object.values(http).forEach((mock) => mock.mockReset()))

  it("aligns the web adapter with the B-owned recommendation router", async () => {
    const run = { id: "r1", project_id: "p1", status: "QUEUED", raw_requirement_snapshot: "需求", parsed_requirement: null, provider: null, model: null, prompt_version: null, error: null, created_at: "now", updated_at: "now" }
    http.get
      .mockResolvedValueOnce([run])
      .mockResolvedValueOnce(run)
      .mockResolvedValueOnce([])
    http.post.mockResolvedValue(run)
    http.patch.mockResolvedValue({ id: "confirmation-1" })
    const { recommendationApi } = await import("./recommendation")

    await recommendationApi.detail("p1")
    await recommendationApi.start("p1")
    await recommendationApi.confirm("c1", { campaign_price: "100.00", fulfillment_cycle: "三天" })
    await recommendationApi.confirmMany("r1", ["c1", "c2"])

    expect(http.get).toHaveBeenNthCalledWith(1, "/api/v1/recommendation-projects/p1/runs")
    expect(http.get).toHaveBeenNthCalledWith(2, "/api/v1/recommendation-projects/runs/r1")
    expect(http.get).toHaveBeenNthCalledWith(3, "/api/v1/recommendation-projects/runs/r1/candidates")
    expect(http.post).toHaveBeenCalledWith("/api/v1/recommendation-projects/p1/runs", undefined, { timeoutMs: 300_000 })
    expect(http.patch).toHaveBeenCalledWith("/api/v1/recommendation-projects/candidates/c1/confirmation", { campaign_price: "100.00", fulfillment_cycle: "三天" })
    expect(http.post).toHaveBeenCalledWith("/api/v1/recommendation-projects/runs/r1/confirmations", { candidate_ids: ["c1", "c2"] })
  })
})
