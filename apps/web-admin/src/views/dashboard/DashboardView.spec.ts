import { describe, expect, it } from "vitest"

import source from "./DashboardView.vue?raw"
import productListSource from "../catalog/ProductListView.vue?raw"
import supplierListSource from "../supplier/SupplierListView.vue?raw"

describe("DashboardView", () => {
  it("presents live operations data instead of development progress", () => {
    expect(source).toContain("正常合作供应商")
    expect(source).toContain("进行中的项目")
    expect(source).toContain("待处理事项")
    expect(source).toContain("待办处理流程跑通后接入")
    expect(source).toContain("最近项目")
    expect(source).toContain("快捷入口")
    expect(source).toContain('/products?action=import')
    expect(source).toContain('/suppliers?action=import')
    expect(source).toContain("auth.hasPermission(action.permission)")
    expect(source).toContain("useDashboardStore")
    expect(source).not.toContain("当前建设进度")
    expect(source).not.toContain("开发边界")
    expect(source).not.toContain("Sprint 1")
    expect(source).not.toContain("Local-First")
  })

  it("opens existing import flows from permission-gated shortcuts", () => {
    expect(productListSource).toContain('route.query.action === "import"')
    expect(productListSource).toContain('auth.hasPermission("product:import")')
    expect(productListSource).toContain("importInput.value?.click()")
    expect(supplierListSource).toContain('route.query.action === "import"')
    expect(supplierListSource).toContain('auth.hasPermission("supplier:create")')
    expect(supplierListSource).toContain("openImportDialog()")
  })
})
