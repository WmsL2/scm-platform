import { afterEach, describe, expect, it, vi } from "vitest"

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }))
vi.mock("../shared/http/runtime", () => ({ http }))

describe("account api contracts", () => {
  afterEach(() => vi.clearAllMocks())
  it("sends registration and password bodies without confirmation fields", async () => {
    const { accountApi } = await import("./account")
    await accountApi.register("user", " pass ")
    await accountApi.changePassword(" old ", " new ")
    expect(http.post).toHaveBeenNthCalledWith(1, "/api/v1/auth/register", { username: "user", password: " pass " }, { authenticated: false })
    expect(http.post).toHaveBeenNthCalledWith(2, "/api/v1/auth/change-password", { current_password: " old ", new_password: " new " })
  })
  it("uses dynamic role and permission replacement APIs including empty arrays", async () => {
    const { accountApi } = await import("./account")
    await accountApi.roles(); await accountApi.permissions(); await accountApi.createRole({ role_code: "pricing_operator", role_name: "报价管理员" })
    await accountApi.setUserRoles("u", []); await accountApi.setRolePermissions("r", [])
    expect(http.get).toHaveBeenCalledWith("/api/v1/admin/roles")
    expect(http.get).toHaveBeenCalledWith("/api/v1/admin/permissions")
    expect(http.post).toHaveBeenCalledWith("/api/v1/admin/roles", { role_code: "pricing_operator", role_name: "报价管理员" })
    expect(http.put).toHaveBeenNthCalledWith(1, "/api/v1/admin/users/u/roles", { role_ids: [] })
    expect(http.put).toHaveBeenNthCalledWith(2, "/api/v1/admin/roles/r/permissions", { permission_ids: [] })
  })
  it("requests registration history through the protected paginated endpoint", async () => {
    const { accountApi } = await import("./account")
    await accountApi.registrationHistory(2, 20)
    expect(http.get).toHaveBeenCalledWith("/api/v1/admin/registration-history?page=2&page_size=20")
  })
  it("uses DELETE for user logical deletion", async () => {
    const { accountApi } = await import("./account")
    await accountApi.deleteUser("u")
    expect(http.delete).toHaveBeenCalledWith("/api/v1/admin/users/u")
  })
})
