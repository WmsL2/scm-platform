import { describe, expect, it } from "vitest"
import { percentageToRatio, ratioToPercentage } from "./productPercentage"

describe("product percentage conversion", () => {
  it.each([
    ["0.1970", "19.70"],
    ["0.2290", "22.90"],
    ["0.0801", "8.01"],
    ["0.8400", "84.00"],
    ["-0.0100", "-1.00"],
  ])("converts database ratio %s to exact percentage %s", (ratio, percentage) => {
    expect(ratioToPercentage(ratio)).toBe(percentage)
  })

  it.each([
    ["19.70", "0.1970"],
    ["22.90", "0.2290"],
    ["8.01", "0.0801"],
    ["84", "0.8400"],
    ["-1", "-0.0100"],
  ])("converts percentage %s to exact database ratio %s", (percentage, ratio) => {
    expect(percentageToRatio(percentage)).toBe(ratio)
  })

  it("rounds excess percentage precision to the database four-decimal ratio", () => {
    expect(percentageToRatio("19.705")).toBe("0.1971")
  })
})
