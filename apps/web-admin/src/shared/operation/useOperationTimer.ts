import { onBeforeUnmount, reactive } from "vue"

export type OperationPhase = "idle" | "running" | "done" | "failed" | "cancelled"

export interface OperationTiming {
  label: string
  seconds: number
  phase: OperationPhase
}

export function formatOperationSeconds(seconds: number): string {
  const wholeSeconds = Math.max(0, Math.floor(seconds))
  return `${Math.floor(wholeSeconds / 60)}分${wholeSeconds % 60}秒`
}

export function useOperationTimer() {
  const state = reactive<OperationTiming>({ label: "", seconds: 0, phase: "idle" })
  let startedAt = 0
  let interval: ReturnType<typeof setInterval> | undefined

  function tick(): void {
    state.seconds = Math.max(0, Math.floor((performance.now() - startedAt) / 1000))
  }

  function start(label: string): void {
    if (interval !== undefined) clearInterval(interval)
    state.label = label
    state.seconds = 0
    state.phase = "running"
    startedAt = performance.now()
    interval = setInterval(tick, 250)
  }

  function finish(phase: "done" | "failed" | "cancelled" = "done"): void {
    if (state.phase !== "running") return
    tick()
    if (interval !== undefined) clearInterval(interval)
    interval = undefined
    state.phase = phase
  }

  function cancel(): void {
    if (state.phase === "running") finish("cancelled")
    else if (state.phase !== "idle") state.phase = "cancelled"
  }

  async function measure<T>(label: string, action: () => Promise<T>): Promise<T> {
    start(label)
    try {
      const result = await action()
      finish()
      return result
    } catch (error) {
      finish("failed")
      throw error
    }
  }

  onBeforeUnmount(() => {
    if (interval !== undefined) clearInterval(interval)
  })

  return { state, measure, cancel }
}

export type OperationTimer = ReturnType<typeof useOperationTimer>
