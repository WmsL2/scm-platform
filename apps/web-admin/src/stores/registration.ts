import { defineStore } from "pinia"
import { ref } from "vue"

import { accountApi } from "../api/account"

export const useRegistrationStore = defineStore("registration", () => {
  const pendingCount = ref(0)

  async function refreshPendingCount(): Promise<void> {
    const result = await accountApi.registrations()
    pendingCount.value = result.total
  }

  function setPendingCount(count: number): void {
    pendingCount.value = count
  }

  function clear(): void {
    pendingCount.value = 0
  }

  return { pendingCount, refreshPendingCount, setPendingCount, clear }
})
