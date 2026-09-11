const LEGACY_ACCESS_TOKEN_KEY = "scm-platform.access-token"
window.localStorage.removeItem(LEGACY_ACCESS_TOKEN_KEY)

let accessToken: string | null = null

export function getAccessToken(): string | null {
  return accessToken
}

export function setAccessToken(token: string): void {
  accessToken = token
}

export function clearAccessToken(): void {
  accessToken = null
}
