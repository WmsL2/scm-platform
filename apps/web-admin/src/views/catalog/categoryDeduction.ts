const SCALE = 10_000n

function parseUnitDecimal(value: string): bigint | null {
  if (!/^\d+(?:\.\d{1,4})?$/.test(value)) return null
  const [whole, fraction = ""] = value.split(".")
  const scaled = BigInt(whole) * SCALE + BigInt((fraction + "0000").slice(0, 4))
  return scaled <= SCALE ? scaled : null
}

function formatUnitDecimal(scaled: bigint): string {
  const whole = scaled / SCALE
  const fraction = (scaled % SCALE).toString().padStart(4, "0").replace(/0+$/, "")
  return fraction ? `${whole}.${fraction}` : whole.toString()
}

function formatPercent(scaled: bigint): string {
  const whole = scaled / 100n
  const fraction = (scaled % 100n).toString().padStart(2, "0").replace(/0+$/, "")
  return fraction ? `${whole}.${fraction}` : whole.toString()
}

export function purchaseCoefficientToDeductionRate(value: string): string | null {
  const coefficient = parseUnitDecimal(value)
  return coefficient === null ? null : formatUnitDecimal(SCALE - coefficient)
}

export function purchaseCoefficientToDeductionPercent(value: string): string | null {
  const coefficient = parseUnitDecimal(value)
  return coefficient === null ? null : formatPercent(SCALE - coefficient)
}

export function deductionRateToPurchaseCoefficient(value: string): string | null {
  const deductionRate = parseUnitDecimal(value)
  return deductionRate === null ? null : formatUnitDecimal(SCALE - deductionRate)
}
