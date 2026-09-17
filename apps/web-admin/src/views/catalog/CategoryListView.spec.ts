import { describe, expect, it } from "vitest"

import BasicLayout from "../../layouts/BasicLayout.vue"
import router from "../../router"
import CategoryListView from "./CategoryListView.vue"
import RolesView from "../admin/RolesView.vue"

describe("category RBAC UI contracts", () => {
  const source = (component: { setup?: unknown }) => String(component.setup)
  const render = (component: { render?: unknown }) => String(component.render)

  it("uses category:list for the menu and CRUD permissions for actions", () => {
    expect(render(BasicLayout)).toContain("category:list")
    expect(router.resolve("/categories").meta).toMatchObject({
      requiresAuth: true,
      permission: "category:list",
    })
    expect(render(CategoryListView)).toContain("category:create")
    expect(render(CategoryListView)).toContain("category:update")
    expect(render(CategoryListView)).toContain("category:delete")
    expect(render(CategoryListView)).toContain("product:import")
  })

  it("shows category permissions as a dedicated role module", () => {
    expect(source(RolesView)).toContain("category: \"\\u7C7B\\u76EE\\u7BA1\\u7406\"")
    expect(source(RolesView)).toContain('["system", "supplier", "product", "category"]')
  })
})
