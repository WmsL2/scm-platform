import { computed, ref } from "vue"
import { defineStore } from "pinia"

import { authApi } from "../api/auth"
import { clearAccessToken, getAccessToken, setAccessToken } from "../shared/auth/token"
import type { AuthStatus, CurrentUser, LoginRequest } from "../types/auth"

export const useAuthStore = defineStore("auth", () => {
  const accessToken = ref<string | null>(getAccessToken())
  const currentUser = ref<CurrentUser | null>(null)
  const status = ref<AuthStatus>("idle")
  const initialized = ref(false)
  let restorePromise: Promise<void> | null = null

  const isAuthenticated = computed(
    () => status.value === "authenticated" && currentUser.value !== null,
  )
  const username = computed(() => currentUser.value?.username ?? "")

  function applyToken(token: string): void {
    accessToken.value = token
    setAccessToken(token)
  }

  function clearSession(): void {
    accessToken.value = null
    currentUser.value = null
    status.value = "anonymous"
    initialized.value = true
    clearAccessToken()
  }

  async function loadCurrentUser(): Promise<void> {
    currentUser.value = await authApi.me()
    status.value = "authenticated"
    initialized.value = true
  }

  async function login(payload: LoginRequest): Promise<void> {
    status.value = "loading"
    try {
      const token = await authApi.login(payload)
      applyToken(token.access_token)
      await loadCurrentUser()
    } catch (error) {
      clearSession()
      throw error
    }
  }

  async function restoreSession(): Promise<void> {
    if (initialized.value) return
    if (restorePromise) return restorePromise

    restorePromise = (async () => {
      if (!accessToken.value) {
        clearSession()
        return
      }

      status.value = "loading"
      try {
        await loadCurrentUser()
      } catch {
        clearSession()
      }
    })().finally(() => {
      restorePromise = null
    })

    return restorePromise
  }

  async function logout(): Promise<void> {
    try {
      if (accessToken.value) await authApi.logout()
    } finally {
      clearSession()
    }
  }

  function hasPermission(permission: string): boolean {
    return currentUser.value?.permissions.includes(permission) ?? false
  }

  return {
    accessToken,
    currentUser,
    status,
    initialized,
    isAuthenticated,
    username,
    login,
    logout,
    restoreSession,
    clearSession,
    hasPermission,
  }
})
