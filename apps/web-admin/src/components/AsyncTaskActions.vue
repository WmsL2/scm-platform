<script setup lang="ts">
import { computed, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { bidApi } from "../api/bid"
import { useAuthStore } from "../stores/auth"
import type { AsyncTask } from "../types/asyncTask"

const props = defineProps<{ task: AsyncTask; mappingPermission?: string }>()
const emit = defineEmits<{ changed: [] }>()
const auth = useAuthStore()
const busy = ref(false)
const canOperate = computed(() => {
  const permission = props.task.task_kind === "MAPPING_STRUCTURE_ANALYSIS"
    ? props.mappingPermission ?? "recommendation:create"
    : props.task.task_kind === "TYPE5_PPT_GENERATION" ? "recommendation:export"
    : ["TYPE1_MATCH", "TYPE2_MATCH"].includes(props.task.task_kind) ? "bid:match" : "recommendation:run"
  return auth.hasPermission(permission)
})
const active = computed(() => ["PENDING", "RUNNING"].includes(props.task.status))
async function operate(action: "cancel" | "retry"): Promise<void> {
  if (busy.value) return
  busy.value = true
  try {
    if (action === "cancel") {
      const running = props.task.status === "RUNNING"
      await ElMessageBox.confirm(running
        ? "将请求 Worker 安全停止此任务，已完成的结果保留。正在解析或渲染时可能需要等待当前步骤退出。确定终止？"
        : "确定取消此排队任务？取消后不会再被领取。", running ? "终止任务" : "取消任务", { type: "warning" })
      const result = await bidApi.cancelAsyncTask(props.task.id)
      ElMessage.success(result.status === "CANCELLED" ? "任务已取消" : "已请求终止，等待 Worker 确认")
    } else {
      await bidApi.retryAsyncTask(props.task.id)
      ElMessage.success("任务已重新排队")
    }
    emit("changed")
  } catch (error) {
    if (error !== "cancel" && error !== "close") ElMessage.error(error instanceof Error ? error.message : "任务操作失败")
  } finally { busy.value = false }
}
</script>

<template>
  <div v-if="canOperate" class="task-actions">
    <el-button v-if="active && !task.cancel_requested_at" size="small" :loading="busy" @click="operate('cancel')">{{ task.status === 'PENDING' ? '取消任务' : '终止任务' }}</el-button>
    <el-tag v-else-if="active && task.cancel_requested_at" type="warning">正在终止</el-tag>
    <el-button v-if="task.status === 'FAILED' && task.attempt_count < task.max_attempts" size="small" :disabled="busy" @click="operate('retry')">重试任务</el-button>
  </div>
</template>

<style scoped>
.task-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 6px; }
.task-actions :deep(.el-button + .el-button) { margin-left: 0; }
</style>
