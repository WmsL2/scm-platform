import { beforeEach, describe, expect, it, vi } from "vitest"
import { createPinia, setActivePinia } from "pinia"

import { getAccessToken, setAccessToken } from "../shared/auth/token"
import type { CurrentUser } from "../types/auth"
import { useAuthStore } from "./auth"

const apiMocks = vi.hoisted(() => ({
  login: vi.fn(),
  me: vi.fn(),
  logout: vi.fn(),
}))

vi.mock("../api/auth", () => ({
  isMockMode: true,
  authApi: apiMocks,
}))

const user: CurrentUser = {
  user_id: "00000000-0000-0000-0000-000000000001",
  username: "tester",
  roles: ["tester"],
  permissions: ["supplier:list"],
}

describe("auth store", () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    window.localStorage.clear()
    apiMocks.login.mockReset()
    apiMocks.me.mockReset()
    apiMocks.logout.mockReset()
  })

  it("logs in, stores the access token and loads the current user", async () => {
    apiMocks.login.mockResolvedValue({
      access_token: "test-token",
      token_type: "bearer",
      expires_in: 1800,
    })
    apiMocks.me.mockResolvedValue(user)

    const store = useAuthStore()
    await store.login({ username: "tester", password: "secret" })

    expect(store.isAuthenticated).toBe(true)
    expect(store.currentUser).toEqual(user)
    expect(getAccessToken()).toBe("test-token")
  })

  it("restores an existing session through the me endpoint", async () => {
    setAccessToken("existing-token")
    apiMocks.me.mockResolvedValue(user)

    const store = useAuthStore()
    await store.restoreSession()

    expect(apiMocks.me).toHaveBeenCalledOnce()
    expect(store.username).toBe("tester")
    expect(store.status).toBe("authenticated")
  })

  it("clears local state when session restoration fails", async () => {
    setAccessToken("expired-token")
    apiMocks.me.mockRejectedValue(new Error("expired"))

    const store = useAuthStore()
    await store.restoreSession()

    expect(store.isAuthenticated).toBe(false)
    expect(store.status).toBe("anonymous")
    expect(getAccessToken()).toBeNull()
  })

  it("calls logout and clears the access token", async () => {
    setAccessToken("test-token")
    apiMocks.me.mockResolvedValue(user)
    apiMocks.logout.mockResolvedValue({ status: "logged_out" })
    const store = useAuthStore()
    await store.restoreSession()

    await store.logout()

    expect(apiMocks.logout).toHaveBeenCalledOnce()
    expect(store.isAuthenticated).toBe(false)
    expect(getAccessToken()).toBeNull()
  })
})
