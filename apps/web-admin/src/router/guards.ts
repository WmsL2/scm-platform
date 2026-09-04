import type { Pinia } from "pinia"
import type { Router } from "vue-router"

import { useAuthStore } from "../stores/auth"

function safeRedirect(value: unknown): string {
  return typeof value === "string" && value.startsWith("/") && !value.startsWith("//")
    ? value
    : "/dashboard"
}

export function installRouterGuards(router: Router, pinia: Pinia): void {
  router.beforeEach(async (to) => {
    const auth = useAuthStore(pinia)
    await auth.restoreSession()

    if (to.name === "login" && auth.isAuthenticated) {
      return safeRedirect(to.query.redirect)
    }

    if (to.meta.requiresAuth && !auth.isAuthenticated) {
      return {
        name: "login",
        query: { redirect: to.fullPath },
      }
    }

    if (
      to.meta.permission
      && auth.isAuthenticated
      && !auth.hasPermission(to.meta.permission)
    ) {
      return { name: "forbidden" }
    }

    return true
  })
}
