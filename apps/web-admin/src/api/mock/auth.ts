import { HttpError } from "../../shared/http"
import { getAccessToken } from "../../shared/auth/token"
import type { CurrentUser, LoginRequest, TokenResponse } from "../../types/auth"

const MOCK_TOKEN_PREFIX = "local-mock-token-"
const MOCK_USER: CurrentUser = {
  user_id: "00000000-0000-0000-0000-000000000001",
  username: "admin",
  roles: ["platform_admin"],
  permissions: [
    "system:user:list",
    "system:role:list",
    "supplier:list",
    "supplier:detail",
  ],
}

function wait(milliseconds = 280): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds))
}

export const mockAuthApi = {
  async login(payload: LoginRequest): Promise<TokenResponse> {
    await wait()
    if (payload.username !== "admin" || payload.password !== "admin123") {
      throw new HttpError(401, {
        code: "AUTH_INVALID_CREDENTIALS",
        message: "用户名或密码错误",
      })
    }
    return {
      access_token: `${MOCK_TOKEN_PREFIX}${crypto.randomUUID()}`,
      token_type: "bearer",
      expires_in: 30 * 60,
    }
  },

  async me(): Promise<CurrentUser> {
    await wait(120)
    if (!getAccessToken()?.startsWith(MOCK_TOKEN_PREFIX)) {
      throw new HttpError(401, {
        code: "AUTH_UNAUTHORIZED",
        message: "登录状态已失效",
      })
    }
    return { ...MOCK_USER, roles: [...MOCK_USER.roles], permissions: [...MOCK_USER.permissions] }
  },

  async logout(): Promise<{ status: string }> {
    await wait(100)
    return { status: "logged_out" }
  },
}
