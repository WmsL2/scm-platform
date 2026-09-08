import { createPinia, setActivePinia } from "pinia"
import { afterEach, describe, expect, it, vi } from "vitest"

const registrations = vi.hoisted(() => vi.fn())

vi.mock("../api/account", () => ({
  accountApi: { registrations },
}))

import { useRegistrationStore } from "./registration"

describe("registration store", () => {
  afterEach(() => vi.clearAllMocks())

  it("uses the pending-registration API total for the sidebar badge", async () => {
    setActivePinia(createPinia())
    registrations.mockResolvedValue({ items: [], total: 3, page: 1, page_size: 20 })

    const store = useRegistrationStore()
    await store.refreshPendingCount()

    expect(registrations).toHaveBeenCalledOnce()
    expect(store.pendingCount).toBe(3)
  })

  it("clears the count when the user no longer has a session", () => {
    setActivePinia(createPinia())
    const store = useRegistrationStore()
    store.setPendingCount(2)
    store.clear()
    expect(store.pendingCount).toBe(0)
  })
})
