import { beforeEach, describe, expect, it, vi } from "vitest"

import { HttpClient, HttpError } from "./client"

function response(status: number, body: unknown): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Unauthorized",
    text: vi.fn().mockResolvedValue(JSON.stringify(body)),
  } as unknown as Response
}

describe("HttpClient", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it("adds authorization, request ID and serializes JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(200, {
      code: "OK",
      message: "success",
      data: { access_token: "token" },
    }))
    vi.stubGlobal("fetch", fetchMock)
    const client = new HttpClient({
      baseUrl: "http://api.test/",
      getAuthorization: () => "Bearer current-token",
    })

    const result = await client.post<{ access_token: string }, { username: string }>(
      "/api/v1/auth/login",
      { username: "admin" },
      { requestId: "request-1" },
    )

    expect(result.access_token).toBe("token")
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/v1/auth/login",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
        cache: "no-store",
        body: JSON.stringify({ username: "admin" }),
        headers: expect.objectContaining({
          Authorization: "Bearer current-token",
          "Content-Type": "application/json",
          "X-Request-ID": "request-1",
        }),
      }),
    )
  })

  it("does not send authorization for public requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(200, {
      code: "OK",
      message: "success",
      data: { status: "ok" },
    }))
    vi.stubGlobal("fetch", fetchMock)
    const client = new HttpClient({ getAuthorization: () => "Bearer stale-token" })

    await client.post("/public", {}, { authenticated: false })

    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(requestInit.headers).not.toHaveProperty("Authorization")
  })

  it("notifies the application and throws a typed error on 401", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(401, {
      code: "AUTH_UNAUTHORIZED",
      message: "Authentication required",
    })))
    const onUnauthorized = vi.fn()
    const client = new HttpClient({ onUnauthorized })

    await expect(client.get("/protected")).rejects.toBeInstanceOf(HttpError)
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })

  it("refreshes once and retries the original request with the new token", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response(401, {
        code: "AUTH_UNAUTHORIZED",
        message: "expired",
      }))
      .mockResolvedValueOnce(response(200, {
        code: "OK",
        message: "success",
        data: { value: "restored" },
      }))
    vi.stubGlobal("fetch", fetchMock)
    let authorization = "Bearer expired-token"
    const refreshAuthorization = vi.fn().mockImplementation(async () => {
      authorization = "Bearer refreshed-token"
      return true
    })
    const onUnauthorized = vi.fn()
    const client = new HttpClient({
      getAuthorization: () => authorization,
      refreshAuthorization,
      onUnauthorized,
    })

    await expect(client.get<{ value: string }>("/protected")).resolves.toEqual({
      value: "restored",
    })
    expect(refreshAuthorization).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    const retriedRequest = fetchMock.mock.calls[1]?.[1] as RequestInit
    expect(retriedRequest.headers).toHaveProperty("Authorization", "Bearer refreshed-token")
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it("does not refresh a public 401 or retry after refresh failure", async () => {
    const fetchMock = vi.fn().mockResolvedValue(response(401, {
      code: "AUTH_UNAUTHORIZED",
      message: "expired",
    }))
    vi.stubGlobal("fetch", fetchMock)
    const refreshAuthorization = vi.fn().mockResolvedValue(false)
    const onUnauthorized = vi.fn()
    const client = new HttpClient({ refreshAuthorization, onUnauthorized })

    await expect(client.get("/protected")).rejects.toBeInstanceOf(HttpError)
    await expect(
      client.post("/api/v1/auth/refresh", undefined, { authenticated: false }),
    ).rejects.toBeInstanceOf(HttpError)

    expect(refreshAuthorization).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })
})
