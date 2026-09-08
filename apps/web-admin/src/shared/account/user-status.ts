import type { TagProps } from "element-plus"

const USER_STATUS_LABELS: Record<string, string> = {
  PENDING: "待审批",
  ENABLED: "已启用",
  DISABLED: "已禁用",
  REJECTED: "已拒绝",
}

const USER_STATUS_TAG_TYPES: Record<string, TagProps["type"]> = {
  PENDING: "warning",
  ENABLED: "success",
  DISABLED: "info",
  REJECTED: "danger",
}

export function userStatusLabel(status: string): string {
  return USER_STATUS_LABELS[status] ?? status
}

export function userStatusTagType(status: string): TagProps["type"] {
  return USER_STATUS_TAG_TYPES[status] ?? "info"
}
