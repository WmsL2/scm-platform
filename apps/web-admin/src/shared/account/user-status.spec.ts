import { describe, expect, it } from "vitest"

import { userStatusLabel, userStatusTagType } from "./user-status"

describe("user status presentation", () => {
  it.each([
    ["PENDING", "待审批", "warning"],
    ["ENABLED", "已启用", "success"],
    ["DISABLED", "已禁用", "info"],
    ["REJECTED", "已拒绝", "danger"],
  ] as const)("maps %s to a Chinese label", (status, label, tagType) => {
    expect(userStatusLabel(status)).toBe(label)
    expect(userStatusTagType(status)).toBe(tagType)
  })

  it("keeps an unexpected status visible instead of hiding it", () => {
    expect(userStatusLabel("UNKNOWN")).toBe("UNKNOWN")
    expect(userStatusTagType("UNKNOWN")).toBe("info")
  })
})
