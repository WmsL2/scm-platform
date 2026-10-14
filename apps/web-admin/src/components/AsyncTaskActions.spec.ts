import { flushPromises, mount } from "@vue/test-utils"
import { beforeEach, describe, expect, it, vi } from "vitest"
import AsyncTaskActions from "./AsyncTaskActions.vue"
import type { AsyncTask, AsyncTaskStatus } from "../types/asyncTask"

const mocks = vi.hoisted(() => ({
  confirm: vi.fn(), success: vi.fn(), error: vi.fn(),
  cancelAsyncTask: vi.fn(), retryAsyncTask: vi.fn(),
  permissions: ["bid:match", "recommendation:export", "recommendation:run", "recommendation:create"],
}))
vi.mock("../api/bid", () => ({ bidApi: mocks }))
vi.mock("../stores/auth", () => ({ useAuthStore: () => ({ hasPermission: (value: string) => mocks.permissions.includes(value) }) }))
vi.mock("element-plus", () => ({ ElMessageBox: { confirm: mocks.confirm }, ElMessage: { success: mocks.success, error: mocks.error } }))

function render(status: AsyncTaskStatus, extra: Partial<AsyncTask> = {}) {
  const task: AsyncTask = {
    id: "t1", project_id: "p1", run_id: null, task_kind: "TYPE1_MATCH", status,
    progress_percent: 5, attempt_count: 1, max_attempts: 3, progress_message: null,
    error_code: null, error_message: null, heartbeat_at: null,
    created_at: "2026-10-14T00:00:00", created_by: "u1", ...extra,
  }
  return mount(AsyncTaskActions, { props: { task }, global: { stubs: {
    ElButton: { template: '<button><slot /></button>' }, ElTag: { template: '<span><slot /></span>' },
  } } })
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.permissions = ["bid:match", "recommendation:export", "recommendation:run", "recommendation:create"]
  mocks.confirm.mockResolvedValue("confirm")
  mocks.cancelAsyncTask.mockResolvedValue({ status: "RUNNING" })
})

describe("AsyncTaskActions", () => {
  it.each(["PENDING", "RUNNING"] as const)("offers only stop controls for %s", async (status) => {
    const wrapper = render(status)
    expect(wrapper.text()).toContain(status === "PENDING" ? "取消任务" : "终止任务")
    expect(wrapper.findAll("button")).toHaveLength(1)
    await wrapper.get("button").trigger("click"); await flushPromises()
    expect(mocks.cancelAsyncTask).toHaveBeenCalledWith("t1")
    expect(wrapper.emitted("changed")).toHaveLength(1)
    wrapper.unmount()
  })
  it.each(["SUCCEEDED", "CANCELLED"] as const)("has no action for terminal %s tasks", async (status) => {
    const wrapper = render(status, { attempt_count: 3 })
    expect(wrapper.text()).not.toContain("终止任务")
    expect(wrapper.findAll("button")).toHaveLength(0)
    wrapper.unmount()
  })
  it("offers retry only for a failed task with attempts remaining", async () => {
    mocks.retryAsyncTask.mockResolvedValue({ status: "PENDING" })
    const wrapper = render("FAILED", { attempt_count: 1 })
    expect(wrapper.text()).toContain("重试任务")
    await wrapper.get("button").trigger("click"); await flushPromises()
    expect(mocks.retryAsyncTask).toHaveBeenCalledWith("t1")
    wrapper.unmount()
  })
  it("shows a pending stop state while acknowledgement is pending", () => {
    const wrapper = render("RUNNING", { cancel_requested_at: "2026-10-14T00:01:00" })
    expect(wrapper.text()).toContain("正在终止")
    expect(wrapper.findAll("button")).toHaveLength(0)
    wrapper.unmount()
  })
  it("does not stop when confirmation is dismissed", async () => {
    mocks.confirm.mockRejectedValue("cancel")
    const wrapper = render("RUNNING")
    await wrapper.get("button").trigger("click"); await flushPromises()
    expect(mocks.cancelAsyncTask).not.toHaveBeenCalled()
    expect(mocks.error).not.toHaveBeenCalled()
    wrapper.unmount()
  })
  it("enforces task-kind permissions and never treats bid:update as recommendation access", () => {
    mocks.permissions = ["bid:update"]
    const wrapper = render("FAILED", { task_kind: "MAPPING_STRUCTURE_ANALYSIS" })
    expect(wrapper.findAll("button")).toHaveLength(0)
    wrapper.unmount()
  })
  it("uses export permission for PPT controls", () => {
    mocks.permissions = ["recommendation:run"]
    const wrapper = render("RUNNING", { task_kind: "TYPE5_PPT_GENERATION" })
    expect(wrapper.findAll("button")).toHaveLength(0)
    wrapper.unmount()
  })
})
