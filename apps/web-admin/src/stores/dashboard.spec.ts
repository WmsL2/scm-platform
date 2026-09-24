import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"

const summary = vi.hoisted(() => vi.fn())

vi.mock("../api/dashboard", () => ({ dashboardApi: { summary } }))

import { useDashboardStore } from "./dashboard"

describe("dashboard store", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it("shares the pending action count with the sidebar", async () => {
    summary.mockResolvedValue({
      formal_product_count: 10,
      normal_supplier_count: 5,
      active_project_count: 2,
      pending_supplier_count: 1,
      recent_projects: [],
    })
    const dashboard = useDashboardStore()
    await dashboard.refresh()
    expect(dashboard.pendingSupplierCount).toBe(1)
    expect(summary).toHaveBeenCalledOnce()
  })

  it("deduplicates concurrent refreshes and clears session data", async () => {
    let resolveSummary: ((value: unknown) => void) | undefined
    summary.mockReturnValue(new Promise((resolve) => { resolveSummary = resolve }))
    const dashboard = useDashboardStore()
    const first = dashboard.refresh()
    const second = dashboard.refresh()
    expect(summary).toHaveBeenCalledOnce()
    resolveSummary?.({ pending_supplier_count: 4, recent_projects: [] })
    await Promise.all([first, second])
    dashboard.clear()
    expect(dashboard.pendingSupplierCount).toBe(0)
  })
})
