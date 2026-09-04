import { getAccessToken } from "../auth/token"
import { HttpClient } from "./client"

export const AUTH_UNAUTHORIZED_EVENT = "scm:auth-unauthorized"
export const AUTH_FORBIDDEN_EVENT = "scm:auth-forbidden"

export const http = new HttpClient({
  getAuthorization: () => {
    const token = getAccessToken()
    return token ? `Bearer ${token}` : undefined
  },
  onUnauthorized: () => window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT)),
  onForbidden: () => window.dispatchEvent(new Event(AUTH_FORBIDDEN_EVENT)),
})
