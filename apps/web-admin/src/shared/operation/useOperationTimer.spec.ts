import { afterEach, describe, expect, it, vi } from "vitest"
import { createApp, h } from "vue"

import { formatOperationSeconds, useOperationTimer } from "./useOperationTimer"
import productListSource from "../../views/catalog/ProductListView.vue?raw"
import supplierListSource from "../../views/supplier/SupplierListView.vue?raw"
import categoryListSource from "../../views/catalog/CategoryListView.vue?raw"
import bidProjectListSource from "../../views/bid/BidProjectListView.vue?raw"
import bidProjectDetailSource from "../../views/bid/BidProjectDetailView.vue?raw"

afterEach(() => vi.useRealTimers())

describe("import and export operation timing", () => {
  it("formats elapsed time in minutes and seconds", () => {
    expect(formatOperationSeconds(0)).toBe("0分0秒")
    expect(formatOperationSeconds(61)).toBe("1分1秒")
    expect(formatOperationSeconds(3601)).toBe("60分1秒")
  })

  it("updates while a request runs and keeps the duration after success or failure", async () => {
    vi.useFakeTimers()
    let timer!: ReturnType<typeof useOperationTimer>
    const app = createApp({
      setup() {
        timer = useOperationTimer()
        return () => h("div")
      },
    })
    app.mount(document.createElement("div"))

    let complete!: (value: string) => void
    const pending = timer.measure("商品导出", () => new Promise<string>((resolve) => { complete = resolve }))
    expect(timer.state).toMatchObject({ label: "商品导出", seconds: 0, phase: "running" })
    vi.advanceTimersByTime(61_000)
    expect(timer.state.seconds).toBe(61)
    complete("ready")
    await expect(pending).resolves.toBe("ready")
    expect(timer.state).toMatchObject({ seconds: 61, phase: "done" })

    await expect(timer.measure("供应商导入", () => Promise.reject(new Error("network"))))
      .rejects.toThrow("network")
    expect(timer.state).toMatchObject({ label: "供应商导入", seconds: 0, phase: "failed" })
    app.unmount()
  })

  it("covers imports, exports and bid file downloads, but not template downloads", () => {
    for (const [source, labels] of [
      [productListSource, ["商品导入预览", "商品确认导入", "商品导出", "不通过行导出"]],
      [supplierListSource, ["供应商导入预览", "供应商确认导入"]],
      [categoryListSource, ["类目导入"]],
      [bidProjectListSource, ["投标 Excel 导入"]],
      [bidProjectDetailSource, ["报价文件导出", "投标文件下载"]],
    ] as const) {
      expect(source).toContain("OperationDuration")
      for (const label of labels) expect(source).toContain(`operationTimer.measure("${label}"`)
    }
    for (const [source, label] of [
      [productListSource, "商品模板下载"],
      [supplierListSource, "供应商模板下载"],
      [categoryListSource, "类目模板下载"],
    ] as const) {
      expect(source).not.toContain(`operationTimer.measure("${label}"`)
    }
  })
})
