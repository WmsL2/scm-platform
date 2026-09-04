import { createPinia, setActivePinia } from "pinia"
import { createMemoryHistory, createRouter } from "vue-router"
import { beforeEach, describe, expect, it } from "vitest"

import { clearAccessToken } from "../shared/auth/token"
import { useAuthStore } from "../stores/auth"
import { installRouterGuards } from "./guards"

const page = { template: "<div />" }

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/login", name: "login", component: page },
      { path: "/dashboard", name: "dashboard", component: page, meta: { requiresAuth: true } },
      {
        path: "/protected",
        name: "protected",
        component: page,
        meta: { requiresAuth: true, permission: "supplier:update" },
      },
      { path: "/403", name: "forbidden", component: page, meta: { requiresAuth: true } },
    ],
  })
}

describe("router guards", () => {
  beforeEach(() => {
    window.localStorage.clear()
    clearAccessToken()
  })

  it("redirects anonymous users to login and keeps the requested path", async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const router = createTestRouter()
    installRouterGuards(router, pinia)

    await router.push("/dashboard")
    await router.isReady()

    expect(router.currentRoute.value.name).toBe("login")
    expect(router.currentRoute.value.query.redirect).toBe("/dashboard")
  })

  it("redirects authenticated users without the required permission to 403", async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore(pinia)
    auth.initialized = true
    auth.status = "authenticated"
    auth.currentUser = {
      user_id: "00000000-0000-0000-0000-000000000002",
      username: "limited-user",
      roles: ["viewer"],
      permissions: ["supplier:list"],
    }
    const router = createTestRouter()
    installRouterGuards(router, pinia)

    await router.push("/protected")
    await router.isReady()

    expect(router.currentRoute.value.name).toBe("forbidden")
  })
})
