import { afterEach, describe, expect, it, vi } from "vitest"

import { clearAccessToken, setAccessToken } from "../shared/auth/token"

describe("auth api development mock", () => {
  afterEach(() => {
    clearAccessToken()
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
})
