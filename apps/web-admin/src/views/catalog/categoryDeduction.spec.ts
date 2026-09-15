import { describe, expect, it } from "vitest"
import {
  deductionRateToPurchaseCoefficient,
  purchaseCoefficientToDeductionPercent,
  purchaseCoefficientToDeductionRate,
} from "./categoryDeduction"

describe("Category purchase coefficient conversion", () => {
  it.each([
    ["0.95", "0.05"],
    ["0.92", "0.08"],
    ["0.925", "0.075"],
    ["0.9375", "0.0625"],
    ["1", "0"],
    ["0", "1"],
  ])("converts purchase coefficient %s to deduction rate %s", (coefficient, deductionRate) => {
    expect(purchaseCoefficientToDeductionRate(coefficient)).toBe(deductionRate)
  })

  it.each([
    ["0.95", "5"],
    ["0.92", "8"],
    ["0.925", "7.5"],
    ["0.9375", "6.25"],
  ])("converts purchase coefficient %s to deduction percent %s", (coefficient, deductionPercent) => {
    expect(purchaseCoefficientToDeductionPercent(coefficient)).toBe(deductionPercent)
  })

  it.each([
    ["0.0500", "0.95"],
    ["0.0800", "0.92"],
    ["0.0750", "0.925"],
    ["0.0625", "0.9375"],
  ])("converts deduction rate %s to purchase coefficient %s", (deductionRate, coefficient) => {
    expect(deductionRateToPurchaseCoefficient(deductionRate)).toBe(coefficient)
  })

  it.each(["1.01", "-0.01", "abc", "NaN", "Infinity", "0.93755", ""])("rejects invalid purchase coefficient %s", (coefficient) => {
    expect(purchaseCoefficientToDeductionRate(coefficient)).toBeNull()
    expect(purchaseCoefficientToDeductionPercent(coefficient)).toBeNull()
  })
})
