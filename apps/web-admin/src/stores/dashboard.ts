import { computed, ref } from "vue"
import { defineStore } from "pinia"

import { dashboardApi } from "../api/dashboard"
import type { DashboardSummary } from "../types/dashboard"

export const useDashboardStore = defineStore("dashboard", () => {
  const summary = ref<DashboardSummary>()
  const loading = ref(false)
  const loadFailed = ref(false)
  let refreshPromise: Promise<void> | undefined

  const pendingSupplierCount = computed(() => summary.value?.pending_supplier_count ?? 0)

  function refresh(): Promise<void> {
    if (refreshPromise) return refreshPromise
    loading.value = true
    loadFailed.value = false
    refreshPromise = dashboardApi.summary()
      .then((result) => { summary.value = result })
      .catch(() => {
        summary.value = undefined
        loadFailed.value = true
      })
      .finally(() => {
        loading.value = false
        refreshPromise = undefined
      })
    return refreshPromise
  }

  function clear(): void {
    summary.value = undefined
    loadFailed.value = false
  }

  return {
    summary,
    loading,
    loadFailed,
    pendingSupplierCount,
    refresh,
    clear,
  }
})
