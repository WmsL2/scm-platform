<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useRoute, useRouter } from "vue-router"
import { bidApi } from "../../api/bid"
import { HttpError } from "../../shared/http"
import OperationDuration from "../../shared/operation/OperationDuration.vue"
import { useOperationTimer } from "../../shared/operation/useOperationTimer"
import { useAuthStore } from "../../stores/auth"
import {
  FILE_TYPE_LABELS,
  IMPORT_STATUS_LABELS,
  PROJECT_STATUS_LABELS,
  type BidProjectDetail,
} from "../../types/bid"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const id = String(route.params.id)
const project = ref<BidProjectDetail>()
const loading = ref(false)
const saving = ref(false)
const operationTimer = useOperationTimer()
const editVisible = ref(false)
const voidVisible = ref(false)
const submitVisible = ref(false)
const submitFile = ref("")
const submitNote = ref("")
const voidReason = ref("")
const form = reactive({
  project_name: "",
  buyer_name: "",
  start_at: "" as string | null,
  deadline_at: "" as string | null,
  remark: "" as string | null,
})

const editableStatuses = ["IMPORTED", "MATCHING", "SELECTING", "READY", "EXPORTED"]
const canEdit = computed(() => auth.hasPermission("bid:update") && editableStatuses.includes(project.value?.status ?? ""))
const canVoid = computed(() => auth.hasPermission("bid:void") && editableStatuses.includes(project.value?.status ?? ""))
const canStartMatching = computed(() => project.value?.status === "IMPORTED" && project.value.import_status === "PARSED" && auth.hasPermission("bid:match"))
const canExport = computed(() => ["READY", "EXPORTED"].includes(project.value?.status ?? "") && auth.hasPermission("bid:export"))
const canSubmit = computed(() => project.value?.status === "EXPORTED" && auth.hasPermission("bid:submit"))
const canRecordResult = computed(() => project.value?.status === "SUBMITTED" && auth.hasPermission("bid:result"))
const files = computed(() => project.value?.files ?? [])
const quotedExports = computed(() => files.value.filter((file) => file.file_type === "QUOTED_EXPORT"))

const eventLabels: Record<string, string> = {
  PROJECT_CREATED: "项目创建",
  PROJECT_UPDATED: "项目信息更新",
  PROJECT_VOIDED: "项目作废",
  MATCH_STARTED: "开始商品匹配",
  MATCH_COMPLETED: "商品匹配完成",
  PROJECT_READY: "全部需求处理完成",
  ITEM_SELECTED: "完成选品",
  ITEM_NO_QUOTE: "标记无法报价",
  QUOTE_EXPORTED: "生成报价文件",
  PROJECT_SUBMITTED: "已投标",
  PROJECT_WON: "中标",
  PROJECT_LOST: "未中标",
}

function messageFor(error: unknown, fallback: string) {
  return error instanceof HttpError ? error.response.message : fallback
}

async function load() {
  loading.value = true
  try {
    project.value = await bidApi.get(id)
  } catch (error) {
    ElMessage.error(messageFor(error, "加载项目详情失败"))
  } finally {
    loading.value = false
  }
}

function openEdit() {
  if (!project.value) return
  Object.assign(form, {
    project_name: project.value.project_name,
    buyer_name: project.value.buyer_name,
    start_at: project.value.start_at,
    deadline_at: project.value.deadline_at,
    remark: project.value.remark,
  })
  editVisible.value = true
}

async function saveEdit() {
  if (!form.project_name.trim() || !form.buyer_name.trim()) return ElMessage.error("请填写项目名称和需求商")
  if (form.start_at && form.deadline_at && form.start_at > form.deadline_at) return ElMessage.error("项目开始时间不能晚于投标截止时间")
  saving.value = true
  try {
    await bidApi.update(id, {
      project_name: form.project_name.trim(), buyer_name: form.buyer_name.trim(), start_at: form.start_at || null,
      deadline_at: form.deadline_at || null, remark: form.remark?.trim() || null,
    })
    editVisible.value = false
    ElMessage.success("项目信息已更新")
    await load()
  } catch (error) {
    ElMessage.error(messageFor(error, "更新失败"))
  } finally {
    saving.value = false
  }
}

async function voidProject() {
  if (!voidReason.value.trim()) return ElMessage.error("请填写作废原因")
  saving.value = true
  try {
    await bidApi.voidProject(id, { reason: voidReason.value.trim() })
    voidVisible.value = false
    ElMessage.success("项目已作废")
    await load()
  } catch (error) {
    ElMessage.error(messageFor(error, "作废失败"))
  } finally {
    saving.value = false
  }
}

async function startMatching() {
  try {
    await ElMessageBox.confirm("将对已解析需求行启动商品匹配，是否继续？", "开始商品匹配")
    saving.value = true
    await bidApi.startMatching(id)
    ElMessage.success("商品匹配完成")
    await load()
  } catch (error) {
    if (error !== "cancel" && error !== "close") ElMessage.error(messageFor(error, "启动匹配失败"))
  } finally {
    saving.value = false
  }
}

async function exportFile() {
  saving.value = true
  try {
    await operationTimer.measure("报价文件导出", () => bidApi.export(id))
    ElMessage.success("报价文件已生成")
    await load()
  } catch (error) {
    ElMessage.error(messageFor(error, "导出失败"))
  } finally {
    saving.value = false
  }
}

async function submitProject() {
  if (!submitFile.value) return ElMessage.error("请选择报价文件")
  saving.value = true
  try {
    await bidApi.submit(id, { submitted_file_id: submitFile.value, note: submitNote.value })
    submitVisible.value = false
    ElMessage.success("投标已提交")
    await load()
  } catch (error) {
    ElMessage.error(messageFor(error, "提交投标失败"))
  } finally {
    saving.value = false
  }
}

async function recordResult(win: boolean) {
  try {
    const { value } = await ElMessageBox.prompt("备注（可选）", win ? "标记中标" : "标记未中标", { inputValue: "" })
    await (win ? bidApi.win(id, value) : bidApi.lose(id, value))
    ElMessage.success(win ? "项目已标记为中标" : "项目已标记为未中标")
    await load()
  } catch (error) {
    if (error !== "cancel" && error !== "close") ElMessage.error(messageFor(error, "保存投标结果失败"))
  }
}

async function download(file: { id: string; original_filename: string }) {
  try {
    const blob = await operationTimer.measure("投标文件下载", () => bidApi.download(id, file.id))
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = file.original_filename
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(messageFor(error, "下载文件失败"))
  }
}

onMounted(() => void load())
</script>

<template>
  <div v-if="project" v-loading="loading" class="detail">
    <div class="actions">
      <el-button @click="router.push('/bid-projects')">返回列表</el-button>
      <el-button type="primary" @click="router.push(`/bid-projects/${id}/workbench`)">进入匹配工作台</el-button>
      <el-button v-if="canEdit" @click="openEdit">编辑项目信息</el-button>
      <el-button v-if="canVoid" type="danger" @click="voidReason = ''; voidVisible = true">作废项目</el-button>
      <el-button v-if="canStartMatching" :loading="saving" @click="startMatching">开始匹配</el-button>
      <el-button v-if="canExport" :loading="saving" @click="exportFile">导出报价文件</el-button>
      <el-button v-if="canSubmit" type="primary" @click="submitFile = ''; submitNote = ''; submitVisible = true">提交投标</el-button>
      <el-button v-if="canRecordResult" type="success" @click="recordResult(true)">标记中标</el-button>
      <el-button v-if="canRecordResult" type="warning" @click="recordResult(false)">标记未中标</el-button>
    </div>
    <OperationDuration :timing="operationTimer.state" />

    <el-descriptions title="项目详情" :column="3" border>
      <el-descriptions-item label="项目编号">{{ project.project_code }}</el-descriptions-item>
      <el-descriptions-item label="项目名称">{{ project.project_name }}</el-descriptions-item>
      <el-descriptions-item label="需求商">{{ project.buyer_name }}</el-descriptions-item>
      <el-descriptions-item label="项目状态">{{ PROJECT_STATUS_LABELS[project.status] }}</el-descriptions-item>
      <el-descriptions-item label="导入状态">{{ IMPORT_STATUS_LABELS[project.import_status] }}</el-descriptions-item>
      <el-descriptions-item label="开始时间">{{ project.start_at ?? "-" }}</el-descriptions-item>
      <el-descriptions-item label="投标截止时间">{{ project.deadline_at ?? "-" }}</el-descriptions-item>
      <el-descriptions-item label="创建时间">{{ project.created_at }}</el-descriptions-item>
      <el-descriptions-item label="备注">{{ project.remark ?? "-" }}</el-descriptions-item>
    </el-descriptions>

    <el-card>
      <template #header>生命周期</template>
      <el-timeline>
        <el-timeline-item v-for="event in project.events" :key="event.id" :timestamp="event.occurred_at">
          {{ eventLabels[event.event_type] ?? event.event_type }} {{ event.note ?? "" }}
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-card>
      <template #header>文件版本</template>
      <el-table :data="files">
        <el-table-column prop="original_filename" label="文件名" />
        <el-table-column label="类型"><template #default="{ row }">{{ FILE_TYPE_LABELS[row.file_type] }}</template></el-table-column>
        <el-table-column prop="created_at" label="创建时间" />
        <el-table-column label="操作"><template #default="{ row }"><el-button v-if="auth.hasPermission('bid:file:download')" link @click="download(row)">下载</el-button></template></el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="editVisible" title="编辑项目信息" width="min(760px, 92vw)">
      <el-form label-position="top" class="grid">
        <el-form-item label="项目名称 *"><el-input v-model="form.project_name" /></el-form-item>
        <el-form-item label="需求商 *"><el-input v-model="form.buyer_name" /></el-form-item>
        <el-form-item label="开始时间"><el-date-picker v-model="form.start_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" /></el-form-item>
        <el-form-item label="投标截止时间"><el-date-picker v-model="form.deadline_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" /></el-form-item>
        <el-form-item class="full" label="备注"><el-input v-model="form.remark" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="editVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="voidVisible" title="作废项目" width="min(600px, 92vw)">
      <el-alert title="作废后将无法继续匹配、选品、报价或投标，但历史需求、选品记录、报价文件和时间线仍会保留。" type="warning" :closable="false" />
      <el-input v-model="voidReason" class="void-reason" type="textarea" :maxlength="2000" placeholder="作废原因 *" />
      <template #footer><el-button @click="voidVisible = false">取消</el-button><el-button type="danger" :loading="saving" @click="voidProject">确认作废</el-button></template>
    </el-dialog>

    <el-dialog v-model="submitVisible" title="提交投标" width="min(600px, 92vw)">
      <el-form label-position="top"><el-form-item label="报价文件 *"><el-select v-model="submitFile" placeholder="请选择已导出的报价文件"><el-option v-for="file in quotedExports" :key="file.id" :label="file.original_filename" :value="file.id" /></el-select></el-form-item><el-form-item label="备注"><el-input v-model="submitNote" type="textarea" :rows="3" /></el-form-item></el-form>
      <template #footer><el-button @click="submitVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="submitProject">确认提交</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.detail { display: grid; gap: 18px; }
.actions { display: flex; flex-wrap: wrap; gap: 10px; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
.full { grid-column: 1 / -1; }
.grid :deep(.el-date-editor), :deep(.el-select) { width: 100%; }
.void-reason { margin-top: 16px; }
@media (max-width: 767px) { .grid { grid-template-columns: 1fr; } }
</style>
