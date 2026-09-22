import { ElLoading, ElMessage } from "element-plus"
import { onBeforeUnmount, onMounted, ref, watch } from "vue"
import { onBeforeRouteLeave } from "vue-router"
import { formatOperationSeconds, type OperationTimer } from "../operation/useOperationTimer"

export const EXCEL_IMPORT_LOCK_MESSAGE =
  "Excel 正在上传并处理，请勿切换页面、刷新或关闭浏览器。大文件处理可能需要数分钟。"

export function canLeaveExcelImport(inProgress: boolean): boolean {
  return !inProgress
}

export function protectExcelImportBeforeUnload(
  event: BeforeUnloadEvent,
  inProgress: boolean,
): boolean {
  if (!inProgress) return false
  event.preventDefault()
  event.returnValue = ""
  return true
}

export function useExcelImportNavigationLock(timer?: OperationTimer) {
  const inProgress = ref(false)
  let loading: ReturnType<typeof ElLoading.service> | null = null

  function start(): void {
    inProgress.value = true
    loading?.close()
    loading = ElLoading.service({
      fullscreen: true,
      lock: true,
      text: EXCEL_IMPORT_LOCK_MESSAGE,
      background: "rgba(15, 23, 42, 0.72)",
    })
  }

  watch(() => timer?.state.seconds, () => {
    if (loading && timer?.state.phase === "running") {
      loading.setText(`${EXCEL_IMPORT_LOCK_MESSAGE} 已耗时 ${formatOperationSeconds(timer.state.seconds)}`)
    }
  })

  function stop(): void {
    loading?.close()
    loading = null
    inProgress.value = false
  }

  function handleBeforeUnload(event: BeforeUnloadEvent): void {
    protectExcelImportBeforeUnload(event, inProgress.value)
  }

  onBeforeRouteLeave(() => {
    if (canLeaveExcelImport(inProgress.value)) return true
    ElMessage.warning(EXCEL_IMPORT_LOCK_MESSAGE)
    return false
  })

  onMounted(() => window.addEventListener("beforeunload", handleBeforeUnload))
  onBeforeUnmount(() => {
    window.removeEventListener("beforeunload", handleBeforeUnload)
    stop()
  })

  return { inProgress, start, stop }
}
