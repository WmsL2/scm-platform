<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useRoute, useRouter } from "vue-router"
import { bidApi } from "../../api/bid"
import { recommendationApi } from "../../api/recommendation"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import { PROJECT_STATUS_LABELS, type BidProjectDetail, type BidProjectStatus } from "../../types/bid"
import {
  RUN_STATUS_LABELS,
  TEMPLATE_MAPPING_FIELDS,
  type FactoryDirectStatus,
  type RecommendationCandidate,
  type RecommendationRun,
  type RecommendationTemplateFile,
  type RecommendationTemplateMapping,
  type RecommendationTemplateStructure,
} from "../../types/recommendation"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const projectId = String(route.params.id)
const loading = ref(false)
const acting = ref(false)
const project = ref<BidProjectDetail>()
const templates = ref<RecommendationTemplateFile[]>([])
const mapping = ref<RecommendationTemplateMapping>()
const templateStructure = ref<RecommendationTemplateStructure>()
const mappingSelections = ref<Record<number, string>>({})
const structureLoading = ref(false)
const run = ref<RecommendationRun | null>(null)
const runHistory = ref<RecommendationRun[]>([])
const selectedCandidates = ref<RecommendationCandidate[]>([])
const activeCandidateId = ref<string>()
const confirmVisible = ref(false)
const selectedCandidate = ref<RecommendationCandidate>()
const supplementText = ref("")
const confirmation = reactive({
  campaign_price: "",
  delivery_status: "",
  inventory_status: "",
  fulfillment_cycle: "",
  evidence: "",
  factory_direct: "PENDING" as FactoryDirectStatus,
})
let pollTimer: ReturnType<typeof setInterval> | undefined

const mappingConfirmed = computed(() => Boolean(mapping.value?.confirmed_at))
const activeRun = computed(() => run.value && ["QUEUED", "ANALYZING", "RETRIEVING", "RANKING"].includes(run.value.status))
const canStart = computed(() => Boolean(
  mappingConfirmed.value
  && !activeRun.value
  && ["IMPORTED", "MATCHING", "SELECTING"].includes(project.value?.status ?? "")
  && auth.hasPermission("recommendation:run"),
))
const confirmedCandidates = computed(() => run.value?.candidates.filter((item) => item.confirmation) ?? [])
const pendingCandidates = computed(() => run.value?.candidates ?? [])
const activeCandidate = computed(() => pendingCandidates.value.find((item) => item.id === activeCandidateId.value))
const selectionEditable = computed(() => project.value?.status === "SELECTING" && auth.hasPermission("recommendation:review"))
const canCompleteSelection = computed(() => selectionEditable.value && confirmedCandidates.value.length > 0)
const canReopenSelection = computed(() => Boolean(
  run.value
  && ["READY", "EXPORTED"].includes(project.value?.status ?? "")
  && confirmedCandidates.value.length > 0
  && auth.hasPermission("recommendation:review"),
))
const canExport = computed(() => Boolean(
  run.value
  && ["READY", "EXPORTED"].includes(project.value?.status ?? "")
  && ["CONFIRMED", "EXPORTED"].includes(run.value.status)
  && run.value.candidates.some((item) => item.confirmation)
  && auth.hasPermission("recommendation:export"),
))
const latestRecommendationExport = computed(() =>
  [...(project.value?.files ?? [])]
    .filter((file) => file.file_type === "RECOMMENDATION_EXPORT")
    .sort((left, right) => right.version_no - left.version_no)[0],
)
const canSubmit = computed(() => project.value?.status === "EXPORTED" && Boolean(latestRecommendationExport.value) && auth.hasPermission("bid:submit"))
const canRecordResult = computed(() => project.value?.status === "SUBMITTED" && auth.hasPermission("bid:result"))
const projectStatusType = computed(() => statusTagType(project.value?.status))
const resultStatuses = new Set(["CANDIDATES_READY", "WAITING_CONFIRMATION", "CONFIRMED", "EXPORTED"])

async function refreshProject() {
  project.value = await bidApi.get(projectId)
}

async function load() {
  loading.value = true
  try {
    await refreshProject()
    if (project.value?.project_type !== "FREE_RECOMMENDATION") {
      ElMessage.warning("该项目不是类型4自由推品项目")
      await router.replace(`/bid-projects/${projectId}`)
      return
    }
    templates.value = await bidApi.recommendationTemplates(projectId)
    const latest = templates.value.at(-1)
    if (latest) {
      mapping.value = await bidApi.recommendationTemplateMapping(projectId, latest.id)
      await loadTemplateStructure()
    }
    try {
      runHistory.value = await recommendationApi.runs(projectId)
      const preferred = runHistory.value.find((item) =>
        resultStatuses.has(item.status) || ["QUEUED", "ANALYZING", "RETRIEVING", "RANKING"].includes(item.status),
      ) ?? runHistory.value[0]
      run.value = preferred ? await recommendationApi.run(preferred.id) : null
    } catch (error) {
      if (!(error instanceof HttpError && error.status === 404)) throw error
      run.value = null
    }
    syncPolling()
  } catch (error) {
    ElMessage.error(messageFor(error, "加载自由推品项目失败"))
  } finally {
    loading.value = false
  }
}

function normalizedHeader(value: string): string {
  return value.trim().toLocaleLowerCase()
}

function rebuildMappingSelections(): void {
  if (!mapping.value || !templateStructure.value) return
  const selected = new Set<string>()
  const next: Record<number, string> = {}
  for (const column of templateStructure.value.columns) {
    if (column.duplicate) continue
    const saved = Object.entries(mapping.value.mapping_json).find(
      ([field, header]) => header === column.header && !selected.has(field),
    )?.[0]
    const exact = TEMPLATE_MAPPING_FIELDS.find(
      (field) => normalizedHeader(field.label) === normalizedHeader(column.header) && !selected.has(field.key),
    )?.key
    const field = saved ?? exact
    if (field) {
      next[column.column_index] = field
      selected.add(field)
    }
  }
  mappingSelections.value = next
}

async function loadTemplateStructure(): Promise<void> {
  if (!mapping.value) return
  structureLoading.value = true
  try {
    templateStructure.value = await bidApi.recommendationTemplateStructure(
      projectId,
      mapping.value.template_file.id,
      { sheet_name: mapping.value.sheet_name, header_row: mapping.value.header_row },
    )
    mapping.value.sheet_name = templateStructure.value.sheet_name
    mapping.value.data_start_row = Math.max(mapping.value.data_start_row, mapping.value.header_row + 1)
    rebuildMappingSelections()
  } catch (error) {
    templateStructure.value = undefined
    mappingSelections.value = {}
    ElMessage.error(messageFor(error, "读取模板列失败"))
  } finally {
    structureLoading.value = false
  }
}

async function changeTemplateSheet(value: string): Promise<void> {
  if (!mapping.value) return
  mapping.value.sheet_name = value
  await loadTemplateStructure()
}

async function changeHeaderRow(value: number | undefined): Promise<void> {
  if (!mapping.value || !value) return
  mapping.value.header_row = value
  mapping.value.data_start_row = Math.max(mapping.value.data_start_row, value + 1)
  await loadTemplateStructure()
}

function mappingFieldUsed(field: string, columnIndex: number): boolean {
  return Object.entries(mappingSelections.value).some(
    ([index, selected]) => Number(index) !== columnIndex && selected === field,
  )
}

function selectedMappingJson(): Record<string, string> {
  if (!templateStructure.value) return {}
  return Object.fromEntries(
    templateStructure.value.columns.flatMap((column) => {
      const field = mappingSelections.value[column.column_index]
      return field && !column.duplicate ? [[field, column.header]] : []
    }),
  )
}

async function saveMapping() {
  if (!mapping.value) return
  if (!mapping.value.sheet_name.trim()) return ElMessage.error("请填写工作表名称")
  if (mapping.value.data_start_row <= mapping.value.header_row) return ElMessage.error("数据起始行必须晚于表头行")
  acting.value = true
  try {
    mapping.value = await bidApi.updateRecommendationTemplateMapping(projectId, mapping.value.template_file.id, {
      sheet_name: mapping.value.sheet_name.trim(),
      header_row: mapping.value.header_row,
      data_start_row: mapping.value.data_start_row,
      mapping_json: selectedMappingJson(),
    })
    await loadTemplateStructure()
    ElMessage.success("模板字段映射已确认")
  } catch (error) {
    ElMessage.error(messageFor(error, "模板映射确认失败"))
  } finally {
    acting.value = false
  }
}

async function startRun() {
  if (!mappingConfirmed.value) return ElMessage.warning("请先确认模板字段映射")
  if (run.value?.candidates.length) {
    try {
      await ElMessageBox.confirm(
        "重新生成会创建一条新的推荐记录，当前候选和确认结果仍会保留在历史记录中。是否继续？",
        "确认重新生成",
        { type: "warning", confirmButtonText: "继续生成", cancelButtonText: "取消" },
      )
    } catch {
      return
    }
  }
  acting.value = true
  try {
    run.value = await recommendationApi.start(projectId)
    await refreshRun(run.value.id)
    await refreshProject()
    runHistory.value = await recommendationApi.runs(projectId)
    if (run.value?.status === "FAILED") ElMessage.error(run.value.error ?? "自由推品任务执行失败")
    else if (run.value?.status === "NEEDS_INPUT") ElMessage.warning(run.value.error ?? "请补充需求信息")
    else if (run.value?.status === "NO_CANDIDATES") ElMessage.warning("没有找到满足当前需求的候选商品")
    else ElMessage.success("自由推品候选已生成")
    syncPolling()
  } catch (error) {
    ElMessage.error(messageFor(error, "启动推荐任务失败"))
  } finally {
    acting.value = false
  }
}

async function submitSupplement() {
  const value = supplementText.value.trim()
  if (!project.value || !run.value) return
  if (value.length < 5) return ElMessage.warning("请填写至少 5 个字符的补充说明")
  acting.value = true
  try {
    const remark = `${run.value.raw_requirement_snapshot.trim()}\n\n补充信息：${value}`
    project.value = await bidApi.update(projectId, {
      project_name: project.value.project_name,
      buyer_name: project.value.buyer_name,
      start_at: project.value.start_at,
      deadline_at: project.value.deadline_at,
      remark,
    })
    supplementText.value = ""
    ElMessage.success("补充信息已保存，正在创建新的推荐任务")
  } catch (error) {
    ElMessage.error(messageFor(error, "补充信息保存失败"))
    acting.value = false
    return
  }
  acting.value = false
  await startRun()
}

async function refreshRun(runId = run.value?.id) {
  if (!runId) return
  try {
    run.value = await recommendationApi.run(runId)
    runHistory.value = runHistory.value.map((item) =>
      item.id === run.value?.id ? { ...item, ...run.value, candidates: [] } : item,
    )
    selectedCandidates.value = []
    syncPolling()
  } catch (error) {
    if (!(error instanceof HttpError && error.status === 404)) ElMessage.error(messageFor(error, "刷新推荐进度失败"))
  }
}

async function switchRun(runId: string) {
  if (run.value?.id === runId) return
  loading.value = true
  try {
    run.value = await recommendationApi.run(runId)
    selectedCandidates.value = []
    syncPolling()
  } catch (error) {
    ElMessage.error(messageFor(error, "加载推荐记录失败"))
  } finally {
    loading.value = false
  }
}

function openConfirmation(candidate: RecommendationCandidate) {
  selectedCandidate.value = candidate
  confirmation.campaign_price = candidate.confirmation?.campaign_price ?? ""
  confirmation.delivery_status = candidate.confirmation?.delivery_status ?? ""
  confirmation.inventory_status = candidate.confirmation?.inventory_status ?? ""
  confirmation.fulfillment_cycle = candidate.confirmation?.fulfillment_cycle ?? ""
  confirmation.evidence = candidate.confirmation?.evidence ?? ""
  confirmation.factory_direct = candidate.confirmation?.factory_direct ?? "PENDING"
  confirmVisible.value = true
}

async function saveConfirmation() {
  if (!selectedCandidate.value || !selectionEditable.value) return
  acting.value = true
  try {
    await recommendationApi.confirm(selectedCandidate.value.id, {
      campaign_price: confirmation.campaign_price || null,
      delivery_status: confirmation.delivery_status || null,
      inventory_status: confirmation.inventory_status || null,
      factory_direct: confirmation.factory_direct,
      fulfillment_cycle: confirmation.fulfillment_cycle || null,
      evidence: confirmation.evidence || null,
    })
    await refreshRun(run.value?.id)
    confirmVisible.value = false
    ElMessage.success("人工确认已保存")
  } catch (error) {
    ElMessage.error(messageFor(error, "保存人工确认失败"))
  } finally {
    acting.value = false
  }
}

async function exportConfirmedCandidates() {
  if (!run.value || !canExport.value) return
  acting.value = true
  try {
    const file = await recommendationApi.export(projectId, run.value.id)
    const blob = await recommendationApi.downloadExport(run.value.id, file.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = file.original_filename
    link.click()
    URL.revokeObjectURL(url)
    await refreshRun(run.value.id)
    await refreshProject()
    ElMessage.success("自由推品结果已导出")
  } catch (error) {
    ElMessage.error(messageFor(error, "导出确认结果失败"))
  } finally {
    acting.value = false
  }
}

function handleCandidateSelection(rows: RecommendationCandidate[]) {
  selectedCandidates.value = rows.filter((item) => !item.confirmation)
}

function canSelectCandidate(candidate: RecommendationCandidate): boolean { return !candidate.confirmation }

function candidateRowClass({ row }: { row: RecommendationCandidate }): string {
  if (row.id === activeCandidateId.value) return "active-candidate-row"
  if (row.confirmation) return "chosen-candidate-row"
  return ""
}

async function confirmSelectedCandidates() {
  if (!run.value || selectedCandidates.value.length === 0) {
    return ElMessage.warning("请先勾选需要确认的候选商品")
  }
  acting.value = true
  try {
    const count = selectedCandidates.value.length
    await recommendationApi.confirmMany(
      run.value.id,
      selectedCandidates.value.map((item) => item.id),
    )
    await refreshRun(run.value.id)
    ElMessage.success(`已批量确认 ${count} 件商品`)
  } catch (error) {
    ElMessage.error(messageFor(error, "批量确认选品失败"))
  } finally {
    acting.value = false
  }
}

function activateCandidate(candidate: RecommendationCandidate) {
  activeCandidateId.value = candidate.id
}

async function addActiveCandidate() {
  if (!activeCandidate.value || !selectionEditable.value) return
  if (activeCandidate.value.confirmation) return ElMessage.info("该商品已加入人工选品")
  acting.value = true
  try {
    await recommendationApi.confirm(activeCandidate.value.id, { factory_direct: "PENDING" })
    await refreshRun(run.value?.id)
    activeCandidateId.value = activeCandidate.value?.id
    ElMessage.success("已加入人工选品")
  } catch (error) {
    ElMessage.error(messageFor(error, "加入人工选品失败"))
  } finally {
    acting.value = false
  }
}

async function removeConfirmedCandidate(candidate: RecommendationCandidate) {
  if (!selectionEditable.value) return
  acting.value = true
  try {
    await recommendationApi.removeConfirmation(candidate.id)
    await refreshRun(run.value?.id)
    ElMessage.success("已从人工选品中移除")
  } catch (error) {
    ElMessage.error(messageFor(error, "移除人工选品失败"))
  } finally {
    acting.value = false
  }
}

async function completeSelection() {
  if (!run.value || !canCompleteSelection.value) return
  try {
    await ElMessageBox.confirm(
      `确认完成选品？当前已选择 ${confirmedCandidates.value.length} 件商品。`,
      "完成选品",
      { type: "warning", confirmButtonText: "确认完成", cancelButtonText: "继续调整" },
    )
  } catch {
    return
  }
  acting.value = true
  try {
    await recommendationApi.completeSelection(projectId, run.value.id)
    await refreshProject()
    ElMessage.success("选品已完成，可以导出确认结果")
  } catch (error) {
    ElMessage.error(messageFor(error, "完成选品失败"))
  } finally {
    acting.value = false
  }
}

async function reopenSelection() {
  if (!run.value || !canReopenSelection.value) return
  try {
    await ElMessageBox.confirm(
      "返回后可以增删人工选品；如已导出，调整完成后需要重新导出新版本。",
      "返回调整选品",
      { type: "warning", confirmButtonText: "返回调整", cancelButtonText: "取消" },
    )
  } catch {
    return
  }
  acting.value = true
  try {
    await recommendationApi.reopenSelection(projectId, run.value.id)
    await Promise.all([refreshProject(), refreshRun(run.value.id)])
    ElMessage.success("已返回待选品状态")
  } catch (error) {
    ElMessage.error(messageFor(error, "返回调整选品失败"))
  } finally {
    acting.value = false
  }
}

async function markSubmitted() {
  const file = latestRecommendationExport.value
  if (!file || !canSubmit.value) return
  let note = ""
  try {
    const result = await ElMessageBox.prompt(
      `将使用 ${file.original_filename} 标记为已投标，可填写提交说明。`,
      "标记已投标",
      { confirmButtonText: "确认提交", cancelButtonText: "取消", inputPlaceholder: "提交说明（选填）" },
    )
    note = result.value
  } catch {
    return
  }
  acting.value = true
  try {
    await bidApi.submit(projectId, { submitted_file_id: file.id, note })
    await refreshProject()
    ElMessage.success("项目已标记为已投标")
  } catch (error) {
    ElMessage.error(messageFor(error, "标记已投标失败"))
  } finally {
    acting.value = false
  }
}

async function recordBidResult(won: boolean) {
  if (!canRecordResult.value) return
  let note = ""
  try {
    const result = await ElMessageBox.prompt(
      won ? "请确认该项目已中标，可填写结果说明。" : "请确认该项目未中标，可填写原因。",
      won ? "登记中标" : "登记未中标",
      { confirmButtonText: "确认登记", cancelButtonText: "取消", inputPlaceholder: won ? "中标说明（选填）" : "未中标原因（选填）" },
    )
    note = result.value
  } catch {
    return
  }
  acting.value = true
  try {
    if (won) await bidApi.win(projectId, note)
    else await bidApi.lose(projectId, note)
    await refreshProject()
    ElMessage.success(won ? "已登记为中标" : "已登记为未中标")
  } catch (error) {
    ElMessage.error(messageFor(error, "登记项目结果失败"))
  } finally {
    acting.value = false
  }
}

function productValue(candidate: RecommendationCandidate, key: string): string {
  const value = candidate.product_snapshot[key] ?? candidate.price_snapshot[key]
  return value === null || value === undefined || value === "" ? "-" : String(value)
}

function statusTagType(status?: BidProjectStatus): "info" | "warning" | "primary" | "success" | "danger" {
  if (status === "MATCHING") return "warning"
  if (status === "SELECTING" || status === "SUBMITTED") return "primary"
  if (status === "READY" || status === "WON") return "success"
  if (status === "LOST") return "danger"
  return "info"
}

function syncPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = activeRun.value ? setInterval(() => void refreshRun(), 3000) : undefined
}

function messageFor(error: unknown, fallback: string): string {
  return error instanceof HttpError ? error.response.message : fallback
}

onMounted(() => void load())
onBeforeUnmount(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<template>
  <div v-loading="loading" class="workspace">
    <header>
      <div><p>FREE RECOMMENDATION</p><div class="project-title"><h1>{{ project?.project_name ?? "自由推品 Agent" }}</h1><el-tag :type="projectStatusType" effect="dark">{{ PROJECT_STATUS_LABELS[project?.status ?? 'IMPORTED'] }}</el-tag></div><span>{{ project?.remark }}</span></div>
      <div class="actions">
        <el-button @click="router.push('/bid-projects')">返回项目</el-button>
        <el-button v-if="['IMPORTED', 'MATCHING', 'SELECTING'].includes(project?.status ?? '')" type="primary" :disabled="!canStart" :loading="acting" @click="startRun">{{ run ? "重新生成推荐" : "开始生成推荐" }}</el-button>
        <el-button v-if="project?.status === 'SELECTING'" type="success" :disabled="!canCompleteSelection" :loading="acting" @click="completeSelection">完成选品</el-button>
        <el-button v-if="['READY', 'EXPORTED'].includes(project?.status ?? '')" :disabled="!canReopenSelection" :loading="acting" @click="reopenSelection">返回调整选品</el-button>
        <el-button v-if="['READY', 'EXPORTED'].includes(project?.status ?? '')" type="success" :disabled="!canExport" :loading="acting" @click="exportConfirmedCandidates">导出已选商品</el-button>
        <el-button v-if="project?.status === 'EXPORTED'" type="primary" :disabled="!canSubmit" :loading="acting" @click="markSubmitted">标记已投标</el-button>
        <el-button v-if="project?.status === 'SUBMITTED'" type="success" :disabled="!canRecordResult" :loading="acting" @click="recordBidResult(true)">登记中标</el-button>
        <el-button v-if="project?.status === 'SUBMITTED'" type="danger" plain :disabled="!canRecordResult" :loading="acting" @click="recordBidResult(false)">登记未中标</el-button>
      </div>
    </header>

    <el-alert v-if="!mappingConfirmed" title="开始推荐前必须人工确认本项目模板的字段映射。毛利、厂直和物流等歧义字段不会由系统自动猜测。" type="warning" :closable="false" />
    <el-card v-if="mapping">
      <template #header><div class="card-header"><strong>结果模板字段映射</strong><el-tag :type="mappingConfirmed ? 'success' : 'warning'">{{ mappingConfirmed ? "已确认" : "待确认" }}</el-tag></div></template>
      <el-alert title="左侧是本次上传模板中的实际列名；右侧选择该列要写入的商品主数据字段。同名列已自动匹配，可搜索或手工调整。" type="info" :closable="false" class="mapping-tip" />
      <div class="mapping-meta">
        <el-select :model-value="mapping.sheet_name" placeholder="选择工作表" @change="changeTemplateSheet"><template #prefix>工作表</template><el-option v-for="name in templateStructure?.sheet_names ?? [mapping.sheet_name]" :key="name" :label="name" :value="name" /></el-select>
        <el-input-number :model-value="mapping.header_row" :min="1" controls-position="right" @change="changeHeaderRow" /><span>表头行</span>
        <el-input-number v-model="mapping.data_start_row" :min="mapping.header_row + 1" controls-position="right" /><span>数据起始行</span>
      </div>
      <div v-loading="structureLoading" class="mapping-table">
        <div class="mapping-table-head"><span>上传模板列（不可修改）</span><span>商品主数据字段（可搜索选择）</span></div>
        <div v-for="column in templateStructure?.columns ?? []" :key="column.column_index" class="mapping-row">
          <div class="template-column"><span class="column-index">{{ column.column_index }}</span><span>{{ column.header }}</span><el-tag v-if="column.duplicate" type="danger" size="small">表头重复，不能映射</el-tag></div>
          <el-select v-model="mappingSelections[column.column_index]" filterable clearable :disabled="column.duplicate" placeholder="搜索并选择商品主数据字段">
            <el-option v-for="field in TEMPLATE_MAPPING_FIELDS" :key="field.key" :label="field.label" :value="field.key" :disabled="mappingFieldUsed(field.key, column.column_index)" />
          </el-select>
        </div>
        <el-empty v-if="!structureLoading && !(templateStructure?.columns.length)" description="当前表头行没有可映射列" :image-size="70" />
      </div>
      <div class="card-actions"><el-button v-if="auth.hasPermission('recommendation:create')" type="primary" :loading="acting" @click="saveMapping">确认字段映射</el-button></div>
    </el-card>

    <el-card v-if="run">
      <template #header><div class="card-header"><strong>Agent 运行状态</strong><div class="run-actions"><el-select :model-value="run.id" style="width: 260px" @change="switchRun"><el-option v-for="item in runHistory" :key="item.id" :label="`${new Date(item.created_at).toLocaleString()} · ${RUN_STATUS_LABELS[item.status]}`" :value="item.id" /></el-select><el-tag>{{ RUN_STATUS_LABELS[run.status] }}</el-tag></div></div></template>
      <el-progress :percentage="run.progress_percent ?? (activeRun ? 50 : 100)" :status="run.status === 'FAILED' ? 'exception' : undefined" />
      <p class="muted">{{ run.progress_message ?? run.error ?? `模型：${run.provider ?? '-'} / ${run.model ?? '-'}` }}</p>
      <el-descriptions v-if="run.parsed_requirement" title="需求理解" :column="2" border>
        <el-descriptions-item label="本次读取的需求" :span="2">{{ run.raw_requirement_snapshot }}</el-descriptions-item>
        <el-descriptions-item label="筛选：明确类目">{{ run.parsed_requirement.explicit_category_keywords?.join('、') || run.parsed_requirement.category_keywords.join('、') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="筛选：协议价">{{ run.parsed_requirement.agreement_price_min ?? '不限' }} ～ {{ run.parsed_requirement.agreement_price_max ?? '不限' }}</el-descriptions-item>
        <el-descriptions-item label="筛选：京东价">{{ run.parsed_requirement.jd_price_min ?? '不限' }} ～ {{ run.parsed_requirement.jd_price_max ?? '不限' }}</el-descriptions-item>
        <el-descriptions-item label="筛选：折扣率 / 点位">{{ run.parsed_requirement.discount_rate_min ?? '不限' }} ～ {{ run.parsed_requirement.discount_rate_max ?? '不限' }} / {{ run.parsed_requirement.gross_margin_min ?? '不限' }} ～ {{ run.parsed_requirement.gross_margin_max ?? '不限' }}</el-descriptions-item>
        <el-descriptions-item label="参考：场景">{{ run.parsed_requirement.scenarios?.join('、') || run.parsed_requirement.scenario_keywords.join('、') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="参考：品牌">{{ run.parsed_requirement.preferred_brands?.join('、') || run.parsed_requirement.required_brands?.join('、') || run.parsed_requirement.brand_keywords.join('、') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="参考：履约/物流">{{ run.parsed_requirement.fulfillment_mode ?? '-' }}</el-descriptions-item>
      </el-descriptions>
      <el-descriptions v-else title="本次 Agent 实际读取的需求" :column="1" border>
        <el-descriptions-item label="需求快照">{{ run.raw_requirement_snapshot }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="run.status === 'NEEDS_INPUT'" class="supplement-box">
        <el-alert :title="run.error ?? '请补充需求信息'" type="warning" :closable="false" />
        <el-input v-model="supplementText" type="textarea" :rows="4" maxlength="3000" show-word-limit placeholder="在这里回答上面的问题。保存后会创建新的 Run，旧需求快照不会被覆盖。" />
        <el-button v-if="auth.hasPermission('bid:update') && auth.hasPermission('recommendation:run')" type="primary" :loading="acting" @click="submitSupplement">保存补充说明并重新生成</el-button>
      </div>
    </el-card>

    <el-card v-if="run?.category_choices.length">
      <template #header><strong>推荐类目方向</strong></template>
      <div class="category-grid"><div v-for="choice in run.category_choices" :key="choice.id" class="category-card"><strong>{{ [choice.level1_name, choice.level2_name, choice.level3_name].filter(Boolean).join(' / ') }}</strong><span>{{ choice.reason }}</span><el-tag size="small">{{ choice.candidate_count }} 个候选</el-tag></div></div>
    </el-card>

    <el-card v-if="run?.candidates.length" class="selection-card">
      <template #header><div class="card-header"><div><strong>推荐商品与人工选品</strong><span class="muted"> 左侧是 Agent 推荐，右侧是最终人工选择。</span></div><div class="selection-summary"><el-tag type="info">推荐 {{ run.candidates.length }} 件</el-tag><el-tag type="success">人工已选 {{ confirmedCandidates.length }} 件</el-tag></div></div></template>
      <div class="selection-workbench">
        <section class="candidate-pane">
          <div class="pane-title"><div><strong>Agent 推荐候选</strong><span>点击商品后整行变蓝，再加入右侧</span></div><div class="pane-actions"><el-button v-if="selectionEditable" type="primary" :disabled="!activeCandidate || Boolean(activeCandidate.confirmation)" :loading="acting" @click="addActiveCandidate">加入人工选品 →</el-button><el-button v-if="selectionEditable" :disabled="selectedCandidates.length === 0" :loading="acting" @click="confirmSelectedCandidates">批量加入（{{ selectedCandidates.length }}）</el-button></div></div>
          <el-table :data="run.candidates" :row-class-name="candidateRowClass" @row-click="activateCandidate" @selection-change="handleCandidateSelection">
            <el-table-column v-if="selectionEditable" type="selection" width="44" :selectable="canSelectCandidate" />
            <el-table-column prop="rank" label="排名" width="62" />
            <el-table-column label="商品" min-width="220"><template #default="{ row }"><strong>{{ productValue(row, 'product_name') }}</strong><div class="muted">{{ productValue(row, 'brand') }} / {{ productValue(row, 'model') }}</div></template></el-table-column>
            <el-table-column label="协议价" width="105"><template #default="{ row }">¥ {{ productValue(row, 'agreement_price') }}</template></el-table-column>
            <el-table-column label="点位" width="80"><template #default="{ row }">{{ productValue(row, 'gross_margin') }}</template></el-table-column>
            <el-table-column prop="score" label="推荐分" width="80" />
            <el-table-column label="状态" width="86"><template #default="{ row }"><el-tag :type="row.confirmation ? 'success' : 'info'" size="small">{{ row.confirmation ? '已加入' : '候选' }}</el-tag></template></el-table-column>
          </el-table>
        </section>
        <section class="confirmed-pane">
          <div class="pane-title"><div><strong>人工选择结果</strong><span>导出文件只包含这里的商品</span></div><el-button v-if="project?.status === 'SELECTING'" type="success" :disabled="!canCompleteSelection" :loading="acting" @click="completeSelection">完成选品</el-button></div>
          <el-empty v-if="confirmedCandidates.length === 0" description="从左侧选择商品加入人工选品" :image-size="72" />
          <div v-else class="confirmed-list">
            <article v-for="candidate in confirmedCandidates" :key="candidate.id" class="confirmed-item">
              <div class="confirmed-rank">{{ candidate.rank }}</div>
              <div class="confirmed-content"><strong>{{ productValue(candidate, 'product_name') }}</strong><span>{{ productValue(candidate, 'brand') }} / {{ productValue(candidate, 'model') }}</span><small>协议价 ¥{{ productValue(candidate, 'agreement_price') }} · 点位 {{ productValue(candidate, 'gross_margin') }}</small></div>
              <div class="confirmed-actions"><el-button link type="primary" @click="openConfirmation(candidate)">{{ selectionEditable ? '完善信息' : '查看信息' }}</el-button><el-button v-if="selectionEditable" link type="danger" @click="removeConfirmedCandidate(candidate)">移除</el-button></div>
            </article>
          </div>
          <div v-if="['READY', 'EXPORTED', 'SUBMITTED', 'WON', 'LOST'].includes(project?.status ?? '')" class="result-footer"><span>选品已锁定，共 {{ confirmedCandidates.length }} 件</span><el-button v-if="['READY', 'EXPORTED'].includes(project?.status ?? '')" type="success" :disabled="!canExport" :loading="acting" @click="exportConfirmedCandidates">导出已选商品</el-button></div>
        </section>
      </div>
    </el-card>

    <el-empty v-if="mappingConfirmed && !run" description="模板已确认，可以开始生成自由推品推荐" />

    <el-dialog v-model="confirmVisible" title="人工确认候选商品" width="min(640px, 92vw)">
      <el-alert v-if="!selectionEditable" title="当前选品已锁定；如需修改，请先返回调整选品。" type="info" :closable="false" class="dialog-alert" />
      <el-form label-position="top" :disabled="!selectionEditable"><el-form-item label="活动价"><el-input v-model="confirmation.campaign_price" inputmode="decimal" /></el-form-item><el-form-item label="发货状态"><el-input v-model="confirmation.delivery_status" /></el-form-item><el-form-item label="库存状态"><el-input v-model="confirmation.inventory_status" /></el-form-item><el-form-item label="是否厂直"><el-select v-model="confirmation.factory_direct"><el-option label="待确认" value="PENDING" /><el-option label="是" value="YES" /><el-option label="否" value="NO" /></el-select></el-form-item><el-form-item label="履约说明"><el-input v-model="confirmation.fulfillment_cycle" type="textarea" :rows="3" /></el-form-item><el-form-item label="依据与备注"><el-input v-model="confirmation.evidence" type="textarea" :rows="3" /></el-form-item></el-form>
      <template #footer><el-button @click="confirmVisible = false">{{ selectionEditable ? '取消' : '关闭' }}</el-button><el-button v-if="selectionEditable" type="primary" :loading="acting" @click="saveConfirmation">确认保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.workspace { display: grid; gap: 18px; }.workspace header { display: flex; justify-content: space-between; gap: 20px; padding: 24px 28px; border-radius: 14px; background: linear-gradient(135deg, #edf5ff, #f2f8f5); }.workspace h1 { margin: 4px 0; }.workspace header p { margin: 0; color: #2670ca; font-weight: 700; }.project-title { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }.actions, .card-header, .run-actions, .mapping-meta, .card-actions, .selection-summary, .pane-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }.card-header { justify-content: space-between; }.mapping-tip { margin-bottom: 16px; }.mapping-meta { margin-bottom: 16px; }.mapping-meta .el-select { width: 280px; }.mapping-table { overflow: hidden; border: 1px solid #e4e7ed; border-radius: 8px; }.mapping-table-head, .mapping-row { display: grid; grid-template-columns: minmax(240px, 1fr) minmax(280px, 1fr); gap: 16px; align-items: center; padding: 10px 14px; }.mapping-table-head { background: #f5f7fa; color: #606266; font-weight: 600; }.mapping-row + .mapping-row { border-top: 1px solid #ebeef5; }.template-column { display: flex; align-items: center; gap: 10px; min-width: 0; }.column-index { display: inline-grid; place-items: center; width: 26px; height: 26px; flex: 0 0 auto; border-radius: 50%; background: #ecf5ff; color: #409eff; font-size: 12px; }.card-actions { justify-content: flex-end; margin-top: 16px; }.category-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; }.category-card { display: grid; gap: 10px; padding: 16px; border: 1px solid #e4e7ed; border-radius: 10px; }.muted { color: #909399; font-size: 13px; }.el-progress + .muted { margin-bottom: 18px; }
.selection-workbench { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(360px, .85fr); gap: 16px; align-items: start; }.candidate-pane, .confirmed-pane { min-width: 0; overflow: hidden; border: 1px solid #dcdfe6; border-radius: 12px; background: #fff; }.confirmed-pane { position: sticky; top: 16px; }.pane-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 48px; padding: 12px 16px; border-bottom: 1px solid #ebeef5; background: #f7f9fc; }.pane-title > div:first-child { display: grid; gap: 3px; }.pane-title span { color: #909399; font-size: 12px; }.confirmed-list { display: grid; gap: 10px; max-height: 620px; padding: 12px; overflow: auto; }.confirmed-item { display: grid; grid-template-columns: 32px minmax(0, 1fr) auto; gap: 10px; align-items: start; padding: 12px; border: 1px solid #c6e2ff; border-radius: 10px; background: #f0f7ff; }.confirmed-rank { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: #409eff; color: #fff; font-weight: 700; }.confirmed-content { display: grid; gap: 5px; min-width: 0; }.confirmed-content strong { line-height: 1.45; }.confirmed-content span, .confirmed-content small { color: #606266; }.confirmed-actions { display: grid; justify-items: end; }.result-footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 16px; border-top: 1px solid #d9ecff; background: #f0f9eb; color: #529b2e; font-weight: 600; }
:deep(.el-table .active-candidate-row > td.el-table__cell) { background: #d9ecff !important; }:deep(.el-table .active-candidate-row:hover > td.el-table__cell) { background: #c6e2ff !important; }:deep(.el-table .chosen-candidate-row > td.el-table__cell) { background: #f0f9eb; }
.supplement-box { display: grid; gap: 12px; margin-top: 18px; justify-items: start; }.supplement-box .el-textarea { width: 100%; }
.dialog-alert { margin-bottom: 14px; }
@media (max-width: 1100px) { .selection-workbench { grid-template-columns: 1fr; }.confirmed-pane { position: static; } }
@media (max-width: 767px) { .workspace header { flex-direction: column; }.mapping-table-head { display: none; }.mapping-row { grid-template-columns: 1fr; gap: 8px; }.pane-title, .result-footer { align-items: flex-start; flex-direction: column; }.confirmed-item { grid-template-columns: 32px minmax(0, 1fr); }.confirmed-actions { grid-column: 2; grid-auto-flow: column; } }
</style>
