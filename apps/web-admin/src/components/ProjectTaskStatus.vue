<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { bidApi } from "../api/bid"
import type { AsyncTask } from "../types/asyncTask"
import { ASYNC_TASK_KIND_LABELS } from "../types/asyncTask"
import AsyncTaskActions from "./AsyncTaskActions.vue"

const props = defineProps<{ projectId: string; mappingPermission?: string }>()
const emit = defineEmits<{ active: [value: boolean]; settled: [] }>()
const tasks = ref<AsyncTask[]>([])
const historyVisible = ref(false)
const history = ref<AsyncTask[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
let timer: ReturnType<typeof setTimeout> | undefined
let disposed = false
let previousActive = false
let previousSignature: string | undefined
let refreshSequence = 0
let historySequence = 0
const labels: Record<string, string> = { PENDING: "排队中", RUNNING: "执行中", SUCCEEDED: "已完成", FAILED: "失败", CANCELLED: "已取消" }
const visible = computed(() => tasks.value.filter((task) => ["PENDING", "RUNNING", "FAILED"].includes(task.status)).slice(0, 3))
function active(task: AsyncTask): boolean { return task.status === "PENDING" || task.status === "RUNNING" }
async function loadHistory(): Promise<void> {
  const sequence = ++historySequence
  try {
    const page = await bidApi.asyncTasks(props.projectId, historyPage.value)
    if (disposed || sequence !== historySequence) return
    history.value = page.items
    historyTotal.value = page.total
    if (!page.items.length && historyPage.value > 1) { historyPage.value -= 1; await loadHistory() }
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : "读取任务记录失败") }
}
async function refresh(): Promise<void> {
  const sequence = ++refreshSequence
  if (timer) clearTimeout(timer)
  try {
    const page = await bidApi.asyncTasks(props.projectId)
    if (disposed || sequence !== refreshSequence) return
    tasks.value = page.items
    const hasHeavy = page.items.some((task) => active(task) && task.task_kind !== "MAPPING_STRUCTURE_ANALYSIS")
    emit("active", hasHeavy)
    const signature = page.items.filter((task) => task.task_kind !== "MAPPING_STRUCTURE_ANALYSIS").map((task) => `${task.id}:${task.status}:${task.run_id}`).join("|")
    if ((previousActive && !hasHeavy) || (previousSignature !== undefined && previousSignature !== signature)) emit("settled")
    previousSignature = signature
    previousActive = hasHeavy
    if (historyVisible.value) await loadHistory()
  } catch { /* The surrounding page owns authentication and network errors. */ }
  finally { if (!disposed && sequence === refreshSequence) timer = setTimeout(() => void refresh(), 2000) }
}
async function afterAction(): Promise<void> {
  if (timer) clearTimeout(timer)
  await refresh()
}
onMounted(() => void refresh())
onBeforeUnmount(() => { disposed = true; if (timer) clearTimeout(timer) })
</script>

<template>
  <div v-if="tasks.length" class="task-status">
    <div><el-button link type="primary" @click="historyVisible = true; loadHistory()">后台任务记录</el-button></div>
    <el-alert v-for="task in visible" :key="task.id" :type="task.status === 'FAILED' ? 'error' : 'info'" :closable="false" :title="`${ASYNC_TASK_KIND_LABELS[task.task_kind] ?? task.task_kind} · ${task.cancel_requested_at && active(task) ? '正在终止' : labels[task.status]} · ${task.progress_message ?? ''}`">
      <p>{{ task.error_message ?? `进度 ${task.progress_percent}%` }} · 创建时间 {{ task.created_at }} · 创建人 {{ task.created_by }} · 最近心跳 {{ task.heartbeat_at ?? '尚未领取' }}</p>
      <AsyncTaskActions :task="task" :mapping-permission="mappingPermission" @changed="afterAction" />
    </el-alert>
    <el-drawer v-model="historyVisible" title="后台任务记录" size="min(1000px, 95vw)" append-to-body>
      <p>此处可终止排队或执行中的任务，或重试失败任务；已结束任务会保留在历史中。</p>
      <el-table :data="history">
        <el-table-column label="任务类型" min-width="160"><template #default="{ row }">{{ ASYNC_TASK_KIND_LABELS[row.task_kind] ?? row.task_kind }}</template></el-table-column>
        <el-table-column label="状态" width="100"><template #default="{ row }">{{ row.cancel_requested_at && active(row) ? '正在终止' : labels[row.status] }}</template></el-table-column>
        <el-table-column prop="created_at" label="创建时间" min-width="180" />
        <el-table-column prop="error_message" label="说明" min-width="180" />
        <el-table-column label="操作" min-width="220"><template #default="{ row }"><AsyncTaskActions :task="row" :mapping-permission="mappingPermission" @changed="afterAction" /></template></el-table-column>
      </el-table>
      <el-pagination v-model:current-page="historyPage" :page-size="10" :total="historyTotal" layout="total, prev, pager, next" @current-change="loadHistory" />
    </el-drawer>
  </div>
</template>

<style scoped>
.task-status { display: grid; gap: 8px; }
p { margin: 6px 0; overflow-wrap: anywhere; }
</style>
