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
    await recommendationApi.updateManualChecks("c1", [{
      code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发",
      required: true, status: "PASS", evidence: "供应商确认",
    }])

    expect(http.get).toHaveBeenNthCalledWith(1, "/api/v1/recommendation-projects/p1/runs")
    expect(http.get).toHaveBeenNthCalledWith(2, "/api/v1/recommendation-projects/runs/r1")
    expect(http.get).toHaveBeenNthCalledWith(3, "/api/v1/recommendation-projects/runs/r1/candidates")
    expect(http.post).toHaveBeenCalledWith("/api/v1/recommendation-projects/p1/runs", undefined, { timeoutMs: 300_000 })
    expect(http.patch).toHaveBeenCalledWith("/api/v1/recommendation-projects/candidates/c1/confirmation", { campaign_price: "100.00", fulfillment_cycle: "三天" })
    expect(http.post).toHaveBeenCalledWith("/api/v1/recommendation-projects/runs/r1/confirmations", { candidate_ids: ["c1", "c2"] })
    expect(http.patch).toHaveBeenCalledWith(
      "/api/v1/recommendation-projects/candidates/c1/manual-checks",
      { checks: [{ code: "DROP_SHIPPING", status: "PASS", evidence: "供应商确认" }] },
    )
  })

  it("keeps complete confirmation data returned by the candidates endpoint", async () => {
    const run = { id: "r1", project_id: "p1", status: "CONFIRMED", raw_requirement_snapshot: "需求", parsed_requirement: null, provider: null, model: null, prompt_version: null, error: null, created_at: "now", updated_at: "now" }
    const confirmation = {
      id: "cf1", candidate_id: "c1", campaign_price: "88", delivery_status: "READY",
      inventory_status: "IN_STOCK", factory_direct: "YES", fulfillment_cycle: "48小时",
      evidence: "供应商确认", confirmed_by: "u1", confirmed_at: "now", updated_at: "now",
    }
    http.get.mockResolvedValueOnce(run).mockResolvedValueOnce([{
      id: "c1", run_id: "r1", product_id: "p1", rank: 1, score: "99", reason: "适合",
      product_snapshot: {}, supplier_snapshot: {}, price_snapshot: {}, confirmation_id: "cf1",
      factory_direct: "YES", confirmation,
    }])
    const { recommendationApi } = await import("./recommendation")

    const result = await recommendationApi.run("r1")

    expect(result.candidates[0].confirmation).toEqual(confirmation)
    expect(result.candidates[0].confirmation?.fulfillment_cycle).toBe("48小时")
  })
})
