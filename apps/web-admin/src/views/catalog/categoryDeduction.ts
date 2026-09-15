export function ratioToPercent(value: string): string | null {
  if (!/^\d+(?:\.\d{1,4})?$/.test(value)) return null
  const [whole, fraction = ""] = value.split(".")
  if ((whole !== "0" && whole !== "1") || (whole === "1" && /[1-9]/.test(fraction))) return null
  const scaled = BigInt(whole) * 10000n + BigInt((fraction + "0000").slice(0, 4))
  const integer = scaled / 100n
  const decimal = (scaled % 100n).toString().padStart(2, "0")
  return decimal === "00" ? integer.toString() : `${integer}.${decimal}`.replace(/0+$/, "")
}
