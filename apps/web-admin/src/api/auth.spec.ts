import { afterEach, describe, expect, it, vi } from "vitest"

import { clearAccessToken, setAccessToken } from "../shared/auth/token"

const http = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
}))

vi.mock("../shared/http/runtime", () => ({ http }))

describe("auth api", () => {
  afterEach(() => {
    clearAccessToken()
    http.get.mockReset()
    http.post.mockReset()
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it("loads the local mock implementation only when explicitly enabled in development", async () => {
    vi.stubEnv("VITE_USE_MOCK", "true")
    const { authApi, isMockMode } = await import("./auth")

    expect(isMockMode).toBe(true)
    const token = await authApi.login({ username: "admin", password: "admin123" })
    setAccessToken(token.access_token)

    await expect(authApi.me()).resolves.toMatchObject({ username: "admin" })
  })

  it("uses the real FastAPI endpoints when Mock is explicitly disabled", async () => {
    vi.stubEnv("VITE_USE_MOCK", "false")
    http.post
      .mockResolvedValueOnce({
        access_token: "real-access-token",
        token_type: "bearer",
        expires_in: 1800,
      })
      .mockResolvedValueOnce({ status: "logged_out" })
    http.get.mockResolvedValue({
      user_id: "00000000-0000-0000-0000-000000000001",
      username: "real-user",
      roles: [],
      permissions: [],
    })

    const { authApi, isMockMode } = await import("./auth")
    const credentials = { username: "real-user", password: "secret" }

    expect(isMockMode).toBe(false)
    await expect(authApi.login(credentials)).resolves.toMatchObject({
      access_token: "real-access-token",
    })
    await expect(authApi.me()).resolves.toMatchObject({ username: "real-user" })
    await expect(authApi.logout()).resolves.toEqual({ status: "logged_out" })

    expect(http.post).toHaveBeenNthCalledWith(1, "/api/v1/auth/login", credentials, {
      authenticated: false,
    })
    expect(http.get).toHaveBeenCalledWith("/api/v1/auth/me")
    expect(http.post).toHaveBeenNthCalledWith(2, "/api/v1/auth/logout")
  })
})
