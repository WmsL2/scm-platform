<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { bidApi } from "../api/bid"
import { useAuthStore } from "../stores/auth"
import type { AsyncTask } from "../types/asyncTask"

const props = defineProps<{ projectId: string; mappingPermission?: string }>()
const emit = defineEmits<{ active: [value: boolean]; settled: [] }>()
const auth = useAuthStore()
const tasks = ref<AsyncTask[]>([])
const loading = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined
let disposed = false
let previousActive = false
let previousSignature: string | undefined
const labels: Record<string, string> = { PENDING: "排队中", RUNNING: "执行中", SUCCEEDED: "已完成", FAILED: "失败", CANCELLED: "已取消" }
const visible = computed(() => tasks.value.filter((task) => ["PENDING", "RUNNING", "FAILED"].includes(task.status)).slice(0, 3))
function active(task: AsyncTask): boolean { return task.status === "PENDING" || task.status === "RUNNING" }
function canOperate(task: AsyncTask): boolean {
  if (task.task_kind === "MAPPING_STRUCTURE_ANALYSIS") return auth.hasPermission(props.mappingPermission ?? "recommendation:create")
  return auth.hasPermission(task.task_kind === "TYPE5_PPT_GENERATION" ? "recommendation:export" : ["TYPE1_MATCH", "TYPE2_MATCH"].includes(task.task_kind) ? "bid:match" : "recommendation:run")
}
async function refresh(): Promise<void> {
  try {
    const page = await bidApi.asyncTasks(props.projectId)
    if (disposed) return
    tasks.value = page.items
    const hasHeavy = page.items.some((task) => active(task) && task.task_kind !== "MAPPING_STRUCTURE_ANALYSIS")
    emit("active", hasHeavy)
    const signature = page.items.filter((task) => task.task_kind !== "MAPPING_STRUCTURE_ANALYSIS").map((task) => `${task.id}:${task.status}:${task.run_id}`).join("|")
    if ((previousActive && !hasHeavy) || (previousSignature !== undefined && previousSignature !== signature)) emit("settled")
    previousSignature = signature
    previousActive = hasHeavy
  } catch { /* The surrounding page owns authentication and network errors. */ }
  finally { if (!disposed) timer = setTimeout(() => void refresh(), 2000) }
}
async function operate(task: AsyncTask, retry: boolean): Promise<void> {
  loading.value = true
  try {
    await (retry ? bidApi.retryAsyncTask(task.id) : bidApi.cancelAsyncTask(task.id))
    if (timer) clearTimeout(timer)
    await refresh()
    emit("settled")
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : "任务操作失败") }
  finally { loading.value = false }
}
onMounted(() => void refresh())
onBeforeUnmount(() => { disposed = true; if (timer) clearTimeout(timer) })
</script>

<template>
  <div v-if="visible.length" class="task-status">
    <el-alert v-for="task in visible" :key="task.id" :type="task.status === 'FAILED' ? 'error' : 'info'" :closable="false" :title="`${labels[task.status]} · ${task.progress_message ?? ''}`">
      <p>{{ task.error_message ?? `进度 ${task.progress_percent}%` }} · 创建时间 {{ task.created_at }} · 创建人 {{ task.created_by }} · 最近心跳 {{ task.heartbeat_at ?? '尚未领取' }}</p>
      <el-button v-if="canOperate(task) && task.status === 'PENDING'" :loading="loading" @click="operate(task, false)">取消任务</el-button>
      <el-button v-if="canOperate(task) && task.status === 'FAILED' && task.attempt_count < task.max_attempts" :loading="loading" @click="operate(task, true)">重试任务</el-button>
    </el-alert>
  </div>
</template>

<style scoped>
.task-status { display: grid; gap: 8px; }
p { margin: 6px 0; overflow-wrap: anywhere; }
</style>
