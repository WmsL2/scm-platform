import { http } from "../shared/http/runtime"
import type { CurrentUser, LoginRequest, TokenResponse } from "../types/auth"

export const isMockMode = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK === "true"

type MockAuthApi = typeof import("./mock/auth").mockAuthApi
const mockModulePath = "./mock/auth.ts"

async function callMock<T>(callback: (api: MockAuthApi) => Promise<T>): Promise<T> {
  const { mockAuthApi } = (await import(/* @vite-ignore */ mockModulePath)) as {
    mockAuthApi: MockAuthApi
  }
  return callback(mockAuthApi)
}

export const authApi = {
  login(payload: LoginRequest): Promise<TokenResponse> {
    return isMockMode
      ? callMock((api) => api.login(payload))
      : http.post<TokenResponse, LoginRequest>("/api/v1/auth/login", payload, {
          authenticated: false,
        })
  },

  me(): Promise<CurrentUser> {
    return isMockMode
      ? callMock((api) => api.me())
      : http.get<CurrentUser>("/api/v1/auth/me")
  },

  refresh(): Promise<TokenResponse> {
    return isMockMode
      ? callMock((api) => api.refresh())
      : http.post<TokenResponse>("/api/v1/auth/refresh", undefined, {
          authenticated: false,
        })
  },

  logout(): Promise<{ status: string }> {
    return isMockMode
      ? callMock((api) => api.logout())
      : http.post<{ status: string }>("/api/v1/auth/logout")
  },
}
