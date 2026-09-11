import type { TokenResponse } from "../../types/auth"
import { clearAccessToken, getAccessToken, setAccessToken } from "../auth/token"
import { HttpClient } from "./client"

export const AUTH_UNAUTHORIZED_EVENT = "scm:auth-unauthorized"
export const AUTH_FORBIDDEN_EVENT = "scm:auth-forbidden"

const refreshHttp = new HttpClient()
let refreshPromise: Promise<boolean> | null = null

function refreshAuthorization(): Promise<boolean> {
  if (refreshPromise) return refreshPromise
  refreshPromise = refreshHttp
    .post<TokenResponse>("/api/v1/auth/refresh", undefined, { authenticated: false })
    .then((token) => {
      setAccessToken(token.access_token)
      return true
    })
    .catch(() => {
      clearAccessToken()
      return false
    })
    .finally(() => {
      refreshPromise = null
    })
  return refreshPromise
}

export const http = new HttpClient({
  getAuthorization: () => {
    const token = getAccessToken()
    return token ? `Bearer ${token}` : undefined
  },
  refreshAuthorization,
  onUnauthorized: () => window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT)),
  onForbidden: () => window.dispatchEvent(new Event(AUTH_FORBIDDEN_EVENT)),
})
