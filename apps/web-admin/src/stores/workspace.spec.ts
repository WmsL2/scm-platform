import { beforeEach, describe, expect, it } from "vitest"
import { createPinia, setActivePinia } from "pinia"

import { useWorkspaceStore } from "./workspace"

function route(path: string, title: string) {
  return {
    fullPath: path,
    path,
    meta: { requiresAuth: true, title },
  } as never
}

describe("workspace store tab order", () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it("moves open tabs by draggable index", () => {
    const workspace = useWorkspaceStore()
    workspace.openRoute(route("/suppliers", "供应商管理"))
    workspace.openRoute(route("/products", "商品主数据"))

    workspace.moveByIndex(2, 0)
    expect(workspace.tabs.map((tab) => tab.path)).toEqual(["/products", "/dashboard", "/suppliers"])

    workspace.moveByIndex(1, 2)
    expect(workspace.tabs.map((tab) => tab.path)).toEqual(["/products", "/suppliers", "/dashboard"])
  })

  it("applies the saved preference as routes are opened again", () => {
    const workspace = useWorkspaceStore()
    workspace.openRoute(route("/suppliers", "供应商管理"))
    workspace.openRoute(route("/products", "商品主数据"))
    workspace.moveByIndex(2, 0)

    setActivePinia(createPinia())
    const restored = useWorkspaceStore()
    restored.openRoute(route("/suppliers", "供应商管理"))
    restored.openRoute(route("/products", "商品主数据"))

    expect(restored.tabs.map((tab) => tab.path)).toEqual(["/products", "/dashboard", "/suppliers"])
  })

  it("keeps the preference when open tabs are reset on logout", () => {
    const workspace = useWorkspaceStore()
    workspace.openRoute(route("/products", "商品主数据"))
    workspace.moveByIndex(1, 0)
    workspace.reset()

    workspace.openRoute(route("/products", "商品主数据"))
    expect(workspace.tabs.map((tab) => tab.path)).toEqual(["/products", "/dashboard"])
  })
})
