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

export const useWorkspaceStore = defineStore("workspace", () => {
  const tabs = ref<WorkspaceTab[]>([{ ...DASHBOARD_TAB }])

  function openRoute(route: RouteLocationNormalizedLoaded): void {
    if (!route.meta.requiresAuth || typeof route.meta.title !== "string") return
    if (tabs.value.some((tab) => tab.path === route.fullPath)) return
    tabs.value.push({
      path: route.fullPath,
      title: route.meta.title,
      closable: route.path !== DASHBOARD_TAB.path,
    })
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

  return { tabs, openRoute, close, reset }
})
