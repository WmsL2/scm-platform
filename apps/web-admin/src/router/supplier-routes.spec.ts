import { describe, expect, it } from "vitest"

import router from "./index"

describe("supplier routes", () => {
  it("registers the supplier pages with the frozen permission codes", () => {
    expect(router.resolve("/suppliers").meta).toMatchObject({
      requiresAuth: true,
      permission: "supplier:list",
    })
    expect(router.resolve("/suppliers/new").meta).toMatchObject({
      requiresAuth: true,
      permission: "supplier:create",
    })
    expect(router.resolve("/suppliers/00000000-0000-0000-0000-000000000001").meta).toMatchObject({
      requiresAuth: true,
      permission: "supplier:detail",
    })
    expect(router.resolve("/suppliers/00000000-0000-0000-0000-000000000001/edit").meta).toMatchObject({
      requiresAuth: true,
      permission: "supplier:update",
    })
  })
})
