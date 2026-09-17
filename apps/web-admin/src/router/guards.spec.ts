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
      { path: "/bid-projects", name: "bid-list", component: page, meta: { requiresAuth: true, permission: "bid:list" } },
      { path: "/bid-projects/:id", name: "bid-detail", component: page, meta: { requiresAuth: true, permission: "bid:detail" } },
      { path: "/bid-projects/:id/workbench", name: "bid-workbench", component: page, meta: { requiresAuth: true, permission: "bid:detail" } },
      { path: "/categories", name: "category-list", component: page, meta: { requiresAuth: true, permission: "category:list" } },
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
      role_names: { viewer: "查看者" },
      permissions: ["supplier:list"],
      permission_names: { "supplier:list": "查看供应商" },
    }
    const router = createTestRouter()
    installRouterGuards(router, pinia)

    await router.push("/protected")
    await router.isReady()

    expect(router.currentRoute.value.name).toBe("forbidden")
  })

  it("requires list/detail permissions for bid routes but not bid:select for read-only workbench", async () => {
    const pinia = createPinia(); setActivePinia(pinia)
    const auth = useAuthStore(pinia); auth.initialized = true; auth.status = "authenticated"
    auth.currentUser = { user_id: "00000000-0000-0000-0000-000000000002", username: "viewer", roles: [], role_names: {}, permissions: ["bid:list", "bid:detail"], permission_names: {} }
    const router = createTestRouter(); installRouterGuards(router, pinia)
    await router.push("/bid-projects"); await router.isReady(); expect(router.currentRoute.value.name).toBe("bid-list")
    await router.push("/bid-projects/p1"); expect(router.currentRoute.value.name).toBe("bid-detail")
    await router.push("/bid-projects/p1/workbench"); expect(router.currentRoute.value.name).toBe("bid-workbench")
  })

  it("requires category:list instead of product:list for category management", async () => {
    const pinia = createPinia(); setActivePinia(pinia)
    const auth = useAuthStore(pinia); auth.initialized = true; auth.status = "authenticated"
    auth.currentUser = { user_id: "00000000-0000-0000-0000-000000000002", username: "product-viewer", roles: [], role_names: {}, permissions: ["product:list"], permission_names: {} }
    const router = createTestRouter(); installRouterGuards(router, pinia)
    await router.push("/categories"); await router.isReady(); expect(router.currentRoute.value.name).toBe("forbidden")
  })
})
