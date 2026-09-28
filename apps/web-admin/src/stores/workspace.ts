import { ref } from "vue"
import { defineStore } from "pinia"
import type { RouteLocationNormalizedLoaded } from "vue-router"

export interface WorkspaceTab {
  path: string
  title: string
  closable: boolean
}

const DASHBOARD_TAB: WorkspaceTab = {
  path: "/dashboard",
  title: "工作台",
  closable: false,
}

const WORKSPACE_TAB_ORDER_KEY = "scm.workspace-tab-order.v1"
const MAX_STORED_PATHS = 100

function loadPreferredOrder(): string[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(WORKSPACE_TAB_ORDER_KEY) ?? "[]")
    if (!Array.isArray(value)) return []
    return [...new Set(value.filter((path): path is string => typeof path === "string" && path.startsWith("/")))]
      .slice(0, MAX_STORED_PATHS)
  } catch {
    return []
  }
}

export const useWorkspaceStore = defineStore("workspace", () => {
  const tabs = ref<WorkspaceTab[]>([{ ...DASHBOARD_TAB }])
  const preferredOrder = ref(loadPreferredOrder())

  function sortByPreferredOrder(): void {
    const rank = new Map(preferredOrder.value.map((path, index) => [path, index]))
    tabs.value.sort((left, right) => {
      const leftRank = rank.get(left.path)
      const rightRank = rank.get(right.path)
      if (leftRank === undefined && rightRank === undefined) return 0
      if (leftRank === undefined) return 1
      if (rightRank === undefined) return -1
      return leftRank - rightRank
    })
  }

  function persistOrder(): void {
    const openPaths = new Set(tabs.value.map((tab) => tab.path))
    preferredOrder.value = [
      ...tabs.value.map((tab) => tab.path),
      ...preferredOrder.value.filter((path) => !openPaths.has(path)),
    ].slice(0, MAX_STORED_PATHS)
    try {
      localStorage.setItem(WORKSPACE_TAB_ORDER_KEY, JSON.stringify(preferredOrder.value))
    } catch {
      // Storage can be unavailable in restricted browser modes; dragging still works in memory.
    }
  }

  function openRoute(route: RouteLocationNormalizedLoaded): void {
    if (!route.meta.requiresAuth || typeof route.meta.title !== "string") return
    if (tabs.value.some((tab) => tab.path === route.fullPath)) return
    tabs.value.push({
      path: route.fullPath,
      title: route.meta.title,
      closable: route.path !== DASHBOARD_TAB.path,
    })
    sortByPreferredOrder()
  }

  function moveByIndex(oldIndex: number, newIndex: number): void {
    if (
      oldIndex === newIndex
      || oldIndex < 0
      || newIndex < 0
      || oldIndex >= tabs.value.length
      || newIndex >= tabs.value.length
    ) return
    const [source] = tabs.value.splice(oldIndex, 1)
    tabs.value.splice(newIndex, 0, source)
    persistOrder()
  }

  function close(path: string): string {
    const index = tabs.value.findIndex((tab) => tab.path === path && tab.closable)
    if (index < 0) return DASHBOARD_TAB.path
    tabs.value.splice(index, 1)
    return tabs.value[Math.max(0, index - 1)]?.path ?? DASHBOARD_TAB.path
  }

  function reset(): void {
    tabs.value = [{ ...DASHBOARD_TAB }]
  }

  return { tabs, openRoute, moveByIndex, close, reset }
})
