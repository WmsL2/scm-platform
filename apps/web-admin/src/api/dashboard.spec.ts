import { beforeEach, describe, expect, it, vi } from "vitest"

const { get } = vi.hoisted(() => ({ get: vi.fn() }))

vi.mock("../shared/http/runtime", () => ({
  http: { get },
}))

import { dashboardApi } from "./dashboard"

describe("dashboard api", () => {
  beforeEach(() => vi.clearAllMocks())

  it("loads the live dashboard summary", async () => {
    const summary = {
      formal_product_count: 50,
      normal_supplier_count: 8,
      active_project_count: 3,
      pending_supplier_count: 1,
      recent_projects: [],
    }
    get.mockResolvedValue(summary)

    await expect(dashboardApi.summary()).resolves.toEqual(summary)
    expect(get).toHaveBeenCalledWith("/api/v1/dashboard/summary")
  })
})
