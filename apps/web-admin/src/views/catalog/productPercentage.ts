interface DecimalParts {
  negative: boolean
  integer: string
  fraction: string
}

function decimalParts(value: string): DecimalParts | null {
  const match = value.trim().match(/^([+-]?)(\d*)(?:\.(\d*))?$/)
  if (!match || (!match[2] && !match[3])) return null
  return {
    negative: match[1] === "-",
    integer: (match[2] || "0").replace(/^0+(?=\d)/, ""),
    fraction: match[3] || "",
  }
}

function scaledInteger(value: string, scale: number): bigint | null {
  const parts = decimalParts(value)
  if (!parts) return null
  const keptFraction = parts.fraction.slice(0, scale).padEnd(scale, "0")
  let result = BigInt(`${parts.integer}${keptFraction}`)
  if ((parts.fraction[scale] ?? "0") >= "5") result += 1n
  return parts.negative ? -result : result
}

function formatScaled(value: bigint, scale: number): string {
  const negative = value < 0n
  const digits = (negative ? -value : value).toString().padStart(scale + 1, "0")
  const integer = digits.slice(0, -scale)
  const fraction = digits.slice(-scale)
  return `${negative ? "-" : ""}${integer}.${fraction}`
}

/** Convert the database ratio (0.1970) to an exact UI percentage (19.70). */
export function ratioToPercentage(value: string): string {
  const scaled = scaledInteger(value, 4)
  return scaled === null ? value.trim() : formatScaled(scaled, 2)
}

/** Convert a UI percentage (19.70) to the database's DECIMAL(9,4) ratio (0.1970). */
export function percentageToRatio(value: string): string {
  const scaled = scaledInteger(value, 2)
  return scaled === null ? value.trim() : formatScaled(scaled, 4)
}
