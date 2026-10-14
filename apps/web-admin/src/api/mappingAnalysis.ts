import { http } from "../shared/http/runtime"
import type { AsyncTask } from "../types/asyncTask"

export function isAsyncTask(value: object): value is AsyncTask { return "task_kind" in value }

export async function readMapping<T extends object>(
  read: () => Promise<T | AsyncTask>,
  report: (message: string) => void = () => undefined,
): Promise<T> {
  report("读取缓存中")
  const first = await read()
  if (!isAsyncTask(first)) { report("解析成功"); return first }
  let task = first
  const deadline = Date.now() + 120_000
  while (task.status === "PENDING" || task.status === "RUNNING") {
    report(task.status === "PENDING" ? "后台解析中（排队中）" : "后台解析中")
    if (Date.now() >= deadline) { report("后台解析仍在进行，可稍后刷新"); throw new Error("解析仍在后台进行，请稍后刷新") }
    await new Promise((resolve) => setTimeout(resolve, 1000))
    task = await http.get<AsyncTask>(`/api/v1/bid-projects/async-tasks/${task.id}`)
  }
  if (task.status !== "SUCCEEDED") {
    report("解析失败")
    throw new Error(task.error_message ?? "解析已取消或失败，可在任务面板重试")
  }
  const result = await read()
  if (isAsyncTask(result)) throw new Error("解析结果尚不可用，请稍后刷新")
  report("解析成功")
  return result
}
