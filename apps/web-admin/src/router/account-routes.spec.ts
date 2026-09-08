import { describe, expect, it } from "vitest"
import router from "./index"
describe("account routes", () => {
  it("keeps register anonymous and protects each admin page independently", () => {
    expect(router.resolve("/register").meta.requiresAuth).toBeUndefined()
    expect(router.resolve("/admin/users").meta.permission).toBe("system:user:list")
    expect(router.resolve("/admin/roles").meta.permission).toBe("system:role:list")
    expect(router.resolve("/admin/registrations").meta.permission).toBe("system:registration:list")
  })
})
