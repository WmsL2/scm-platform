import { afterEach, describe, expect, it, vi } from "vitest"
const http = vi.hoisted(() => ({ get: vi.fn() }))
vi.mock("../shared/http/runtime", () => ({ http }))
import { readMapping } from "./mappingAnalysis"

afterEach(() => { vi.useRealTimers(); vi.clearAllMocks() })
describe("mapping task polling", () => {
  it("returns cached data immediately without polling", async () => {
    const read = vi.fn().mockResolvedValue({ sheets: [] })
    expect(await readMapping(read)).toEqual({ sheets: [] })
    expect(http.get).not.toHaveBeenCalled()
  })
  it("polls the task then reads the committed result once", async () => {
    vi.useFakeTimers()
    const task = { id: "t1", task_kind: "MAPPING_STRUCTURE_ANALYSIS", status: "PENDING" }
    const read = vi.fn().mockResolvedValueOnce(task).mockResolvedValueOnce({ columns: [1] })
    http.get.mockResolvedValueOnce({ ...task, status: "RUNNING" }).mockResolvedValueOnce({ ...task, status: "SUCCEEDED" })
    const result = readMapping(read)
    await vi.advanceTimersByTimeAsync(2000)
    expect(await result).toEqual({ columns: [1] })
    expect(read).toHaveBeenCalledTimes(2)
    expect(http.get).toHaveBeenCalledTimes(2)
  })
  it("exposes a terminal parse failure instead of infinite loading", async () => {
    const read = vi.fn().mockResolvedValue({ id: "t1", task_kind: "MAPPING_STRUCTURE_ANALYSIS", status: "FAILED", error_message: "坏工作簿" })
    await expect(readMapping(read)).rejects.toThrow("坏工作簿")
    expect(read).toHaveBeenCalledTimes(1)
  })
})
