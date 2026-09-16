import { beforeEach, describe, expect, it, vi } from "vitest"

const { get } = vi.hoisted(() => ({ get: vi.fn() }))

vi.mock("../shared/http/runtime", () => ({
  http: { get },
}))

import { dashboardApi } from "./dashboard"

describe("dashboard api", () => {
  beforeEach(() => vi.clearAllMocks())

  it("loads the live dashboard summary", async () => {
    get.mockResolvedValue({ formal_product_count: 50, archived_supplier_count: 8 })

    await expect(dashboardApi.summary()).resolves.toEqual({
      formal_product_count: 50,
      archived_supplier_count: 8,
    })
    expect(get).toHaveBeenCalledWith("/api/v1/dashboard/summary")
  })
})
