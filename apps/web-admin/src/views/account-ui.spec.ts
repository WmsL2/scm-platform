import { describe, expect, it } from "vitest"
import BasicLayout from "../layouts/BasicLayout.vue"
import UsersView from "./admin/UsersView.vue"
import RolesView from "./admin/RolesView.vue"
import RegistrationsView from "./admin/RegistrationsView.vue"
import RegisterView from "./auth/RegisterView.vue"

describe("account UI contracts", () => {
  const source = (component: { setup?: unknown }) => String(component.setup)
  const render = (component: { render?: unknown }) => String(component.render)
  it("uses independent permission checks and dynamic management dialogs", () => {
    expect(source(BasicLayout)).toContain("system:user:list")
    expect(source(BasicLayout)).toContain("system:role:list")
    expect(source(BasicLayout)).toContain("system:registration:list")
    expect(render(BasicLayout)).not.toContain("out-in")
    expect(source(UsersView)).toContain("accountApi.roles")
    expect(source(RolesView)).toContain("accountApi.permissions")
    expect(render(RolesView)).toContain("system:role:create")
    expect(source(RolesView)).toContain("accountApi.createRole")
    expect(source(RolesView)).toContain("permissionSubmitting")
    expect(source(RolesView)).toContain("auth.refreshCurrentUser()")
    expect(source(RegistrationsView)).toContain("error.status === 409")
    expect(source(RegistrationsView)).toContain("accountApi.registrationHistory")
  })
  it("keeps registration confirmation local and profile/password contracts explicit", () => {
    expect(source(RegisterView)).toContain("form.confirm")
    expect(source(RegisterView)).toContain("accountApi.register(username, form.password)")
    expect(source(BasicLayout)).toContain("confirm_new_password")
    expect(source(BasicLayout)).toContain("auth.clearSession()")
    expect(source(BasicLayout)).toContain("workspace.reset()")
  })
})
