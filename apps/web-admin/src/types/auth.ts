export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: "bearer"
  expires_in: number
}

export interface CurrentUser {
  user_id: string
  username: string
  roles: string[]
  role_names: Record<string, string>
  permissions: string[]
  permission_names: Record<string, string>
}

export type AuthStatus = "idle" | "loading" | "authenticated" | "anonymous"
