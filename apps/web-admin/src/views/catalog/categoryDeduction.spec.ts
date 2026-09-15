import { describe, expect, it } from "vitest"
import { ratioToPercent } from "./categoryDeduction"

describe("ratioToPercent", () => {
  it.each([
    ["0", "0"],
    ["0.08", "8"],
    ["0.075", "7.5"],
    ["0.0625", "6.25"],
    ["1", "100"],
  ])("converts ratio %s to exact percent %s", (ratio, percent) => {
    expect(ratioToPercent(ratio)).toBe(percent)
  })

  it.each(["", "8", "1.0001", "0.00001", "-0.08", "abc"]) ("rejects invalid ratio %s", (ratio) => {
    expect(ratioToPercent(ratio)).toBeNull()
  })
})
