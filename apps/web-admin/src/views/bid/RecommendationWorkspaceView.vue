<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { Setting } from "@element-plus/icons-vue"
import { useRoute, useRouter } from "vue-router"
import { bidApi } from "../../api/bid"
import { recommendationApi } from "../../api/recommendation"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type { BidProjectDetail } from "../../types/bid"
import {
  RUN_STATUS_LABELS,
  TEMPLATE_MAPPING_FIELDS,
  type FactoryDirectStatus,
  type RecommendationCandidate,
  type RecommendationRun,
  type RecommendationTemplateFile,
  type RecommendationTemplateColumnMappingDocument,
  type RecommendationTemplateMappingJson,
  type RecommendationTemplateMapping,
  type RecommendationTemplateStructure,
} from "../../types/recommendation"
import {
  RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS,
  restoreRecommendationCandidateOptionalColumns,
  updateRecommendationCandidateOptionalColumns,
  type RecommendationCandidateOptionalColumn,
  type RecommendationCandidateOptionalColumnKey,
} from "./recommendationCandidateColumns"

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
const candidatePage = ref(1)
const candidatePageSize = ref(50)
const candidateColumnStorageKey = "scm.recommendation-candidates.visible-columns.v1"
const selectedCandidateOptionalColumns = ref<RecommendationCandidateOptionalColumnKey[]>(
  restoreRecommendationCandidateOptionalColumns(localStorage.getItem(candidateColumnStorageKey)),
)
const selectedCandidateIds = ref<Set<string>>(new Set())
const excludedCandidateIds = ref<Set<string>>(new Set())
const selectAllCandidates = ref(false)
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
const selectionEditable = computed(() => project.value?.status === "SELECTING" && auth.hasPermission("recommendation:review"))
const canStart = computed(() => mappingConfirmed.value && !activeRun.value && ["IMPORTED", "MATCHING", "SELECTING"].includes(project.value?.status ?? "") && auth.hasPermission("recommendation:run"))
const canCompleteSelection = computed(() => selectionEditable.value && (run.value?.candidate_page?.confirmed_total ?? 0) > 0)
const canReopenSelection = computed(() => Boolean(
  run.value && ["READY", "EXPORTED"].includes(project.value?.status ?? "")
    && (run.value.candidate_page?.confirmed_total ?? 0) > 0 && auth.hasPermission("recommendation:review"),
))
const canExport = computed(() => Boolean(
  run.value
  && ["READY", "EXPORTED"].includes(project.value?.status ?? "")
  && ["CONFIRMED", "EXPORTED"].includes(run.value.status)
  && (run.value.candidate_page?.confirmed_total ?? 0) > 0
  && auth.hasPermission("recommendation:export"),
))
const resultStatuses = new Set(["CANDIDATES_READY", "WAITING_CONFIRMATION", "CONFIRMED", "EXPORTED"])
const candidateTotal = computed(() => run.value?.candidate_page?.total ?? 0)
const unconfirmedTotal = computed(() => run.value?.candidate_page?.unconfirmed_total ?? 0)
const selectedCandidateCount = computed(() => selectAllCandidates.value
  ? Math.max(0, unconfirmedTotal.value - excludedCandidateIds.value.size)
  : selectedCandidateIds.value.size)
const selectableOnPage = computed(() => (run.value?.candidates ?? []).filter((item) => !item.confirmation))
const pageAllSelected = computed(() => selectableOnPage.value.length > 0 && selectableOnPage.value.every(isCandidateSelected))
const pagePartiallySelected = computed(() => selectableOnPage.value.some(isCandidateSelected) && !pageAllSelected.value)
const visibleCandidateColumns = computed(() => selectedCandidateOptionalColumns.value
  .map((key) => RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS.find((column) => column.key === key))
  .filter((column): column is RecommendationCandidateOptionalColumn => column !== undefined))

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
      run.value = preferred ? await recommendationApi.run(preferred.id, candidatePage.value, candidatePageSize.value) : null
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

async function refreshProject(): Promise<void> {
  project.value = await bidApi.get(projectId)
}

function normalizedHeader(value: string): string {
  return value.trim().toLocaleLowerCase()
}

function rebuildMappingSelections(): void {
  if (!mapping.value || !templateStructure.value) return
  const next: Record<number, string> = {}
  const savedColumns = isColumnMappingDocument(mapping.value.mapping_json)
    ? new Map(
      mapping.value.mapping_json.columns.map((column) => [column.column_index, column.field_key]),
    )
    : null
  for (const column of templateStructure.value.columns) {
    const saved = savedColumns?.get(column.column_index) ?? (!savedColumns
      ? Object.entries(mapping.value.mapping_json).find(
        ([, header]) => header === column.header,
      )?.[0]
      : undefined)
    const exact = TEMPLATE_MAPPING_FIELDS.find(
      (field) => normalizedHeader(field.label) === normalizedHeader(column.header),
    )?.key
    const field = saved ?? exact
    if (field) {
      next[column.column_index] = field
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

function isColumnMappingDocument(
  mappingJson: RecommendationTemplateMappingJson,
): mappingJson is RecommendationTemplateColumnMappingDocument {
  return "version" in mappingJson && mappingJson.version === 2 && Array.isArray(mappingJson.columns)
}

function selectedMappingJson(): RecommendationTemplateColumnMappingDocument {
  if (!templateStructure.value) return { version: 2, columns: [] }
  return {
    version: 2,
    columns: templateStructure.value.columns.flatMap((column) => {
      const field = mappingSelections.value[column.column_index]
      return field ? [{ column_index: column.column_index, field_key: field }] : []
    }),
  }
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
  if (candidateTotal.value) {
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
    resetCandidateSelection()
    candidatePage.value = 1
    await refreshRun(run.value.id)
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
    run.value = await recommendationApi.run(runId, candidatePage.value, candidatePageSize.value)
    runHistory.value = runHistory.value.map((item) =>
      item.id === run.value?.id ? { ...item, ...run.value, candidates: [] } : item,
    )
    syncPolling()
  } catch (error) {
    if (!(error instanceof HttpError && error.status === 404)) ElMessage.error(messageFor(error, "刷新推荐进度失败"))
  }
}

async function switchRun(runId: string) {
  if (run.value?.id === runId) return
  loading.value = true
  try {
    candidatePage.value = 1
    resetCandidateSelection()
    run.value = await recommendationApi.run(runId, candidatePage.value, candidatePageSize.value)
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
  if (!selectedCandidate.value) return
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
    ElMessage.success("自由推品结果已导出")
  } catch (error) {
    ElMessage.error(messageFor(error, "导出确认结果失败"))
  } finally {
    acting.value = false
  }
}

async function completeSelection(): Promise<void> {
  if (!run.value || !canCompleteSelection.value) return
  try {
    await ElMessageBox.confirm(
      `确认完成选品？当前已确认 ${run.value.candidate_page?.confirmed_total ?? 0} 件商品。`,
      "完成选品", { type: "warning", confirmButtonText: "确认完成", cancelButtonText: "继续调整" },
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

async function reopenSelection(): Promise<void> {
  if (!run.value || !canReopenSelection.value) return
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

function resetCandidateSelection(): void {
  selectedCandidateIds.value = new Set()
  excludedCandidateIds.value = new Set()
  selectAllCandidates.value = false
}

function isCandidateSelected(candidate: RecommendationCandidate): boolean {
  if (candidate.confirmation) return false
  return selectAllCandidates.value
    ? !excludedCandidateIds.value.has(candidate.id)
    : selectedCandidateIds.value.has(candidate.id)
}

function setCandidateSelected(candidate: RecommendationCandidate, selected: boolean): void {
  if (candidate.confirmation) return
  if (selectAllCandidates.value) {
    const excluded = new Set(excludedCandidateIds.value)
    if (selected) excluded.delete(candidate.id)
    else excluded.add(candidate.id)
    excludedCandidateIds.value = excluded
    return
  }
  const ids = new Set(selectedCandidateIds.value)
  if (selected) ids.add(candidate.id)
  else ids.delete(candidate.id)
  selectedCandidateIds.value = ids
}

function setCurrentPageSelected(selected: boolean): void {
  for (const candidate of selectableOnPage.value) setCandidateSelected(candidate, selected)
}

function selectAllUnconfirmedCandidates(): void {
  selectAllCandidates.value = true
  selectedCandidateIds.value = new Set()
  excludedCandidateIds.value = new Set()
}

async function changeCandidatePage(page: number): Promise<void> {
  candidatePage.value = page
  await refreshRun()
}

async function changeCandidatePageSize(pageSize: number): Promise<void> {
  candidatePageSize.value = pageSize
  candidatePage.value = 1
  await refreshRun()
}

async function confirmSelectedCandidates() {
  if (!run.value || selectedCandidateCount.value === 0) {
    return ElMessage.warning("请先勾选需要确认的候选商品")
  }
  acting.value = true
  try {
    const result = await recommendationApi.confirmMany(
      run.value.id,
      selectAllCandidates.value
        ? { selectAll: true, excludedCandidateIds: [...excludedCandidateIds.value] }
        : { candidateIds: [...selectedCandidateIds.value] },
    )
    resetCandidateSelection()
    await refreshRun(run.value.id)
    ElMessage.success(`已批量确认 ${result.confirmed_count} 件商品`)
  } catch (error) {
    ElMessage.error(messageFor(error, "批量确认选品失败"))
  } finally {
    acting.value = false
  }
}

function productValue(candidate: RecommendationCandidate, key: string): string {
  const value = candidate.product_snapshot[key] ?? candidate.price_snapshot[key]
  return value === null || value === undefined || value === "" ? "-" : String(value)
}

function isCandidateColumnSelected(key: RecommendationCandidateOptionalColumnKey): boolean {
  return selectedCandidateOptionalColumns.value.includes(key)
}

function updateCandidateColumnSelection(key: RecommendationCandidateOptionalColumnKey, checked: unknown): void {
  selectedCandidateOptionalColumns.value = updateRecommendationCandidateOptionalColumns(
    selectedCandidateOptionalColumns.value,
    key,
    Boolean(checked),
  )
  localStorage.setItem(candidateColumnStorageKey, JSON.stringify(selectedCandidateOptionalColumns.value))
}

function candidateColumnRawValue(
  candidate: RecommendationCandidate,
  key: RecommendationCandidateOptionalColumnKey,
): unknown {
  if (key === "supplier_name") return candidate.supplier_snapshot.supplier_name
  return candidate.product_snapshot[key] ?? candidate.price_snapshot[key]
}

function moneyValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "-"
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `¥ ${numeric.toFixed(2)}` : String(value)
}

function candidateColumnValue(
  candidate: RecommendationCandidate,
  column: RecommendationCandidateOptionalColumn,
): string {
  const value = candidateColumnRawValue(candidate, column.key)
  if (value === null || value === undefined || value === "") return "-"
  if (column.format === "money") return moneyValue(value)
  if (column.format === "percent") return ratioValue(value)
  return String(value)
}

function candidateImageUrl(candidate: RecommendationCandidate): string | undefined {
  const reference = candidate.product_snapshot.image_reference
  if (typeof reference !== "string" || !reference) return undefined
  if (/^https?:\/\//i.test(reference)) return reference
  const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "")
  return `${baseUrl}/${reference.replace(/^\//, "")}`
}

function ratioValue(value: unknown, fallback = "-"): string {
  if (value === null || value === undefined || value === "") return fallback
  const ratio = Number(value)
  return Number.isFinite(ratio) ? `${(ratio * 100).toFixed(2)}%` : String(value)
}

function specifiedCategoryText(): string {
  const requirement = run.value?.parsed_requirement
  if (!requirement) return "不限"
  const explicit = requirement.explicit_category_keywords ?? []
  if (explicit.length) return explicit.join("、")
  // Compatibility for a run created by the short-lived category-quota version.
  return [...new Set((requirement.category_quotas ?? []).flatMap((item) => item.category_keywords))]
    .join("、") || "不限"
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
      <div><p>FREE RECOMMENDATION</p><h1>{{ project?.project_name ?? "自由推品 Agent" }}</h1><span>{{ project?.remark }}</span></div>
      <div class="actions"><el-button @click="router.push('/bid-projects')">返回项目</el-button><el-button v-if="['IMPORTED', 'MATCHING', 'SELECTING'].includes(project?.status ?? '')" type="primary" :disabled="!canStart" :loading="acting" @click="startRun">{{ run ? "重新生成推荐" : "开始生成推荐" }}</el-button><el-button v-if="project?.status === 'SELECTING'" type="success" :disabled="!canCompleteSelection" :loading="acting" @click="completeSelection">完成选品</el-button><el-button v-if="['READY', 'EXPORTED'].includes(project?.status ?? '')" :disabled="!canReopenSelection" :loading="acting" @click="reopenSelection">返回调整选品</el-button><el-button v-if="['READY', 'EXPORTED'].includes(project?.status ?? '')" type="success" :disabled="!canExport" :loading="acting" @click="exportConfirmedCandidates">导出确认结果</el-button></div>
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
          <div class="template-column"><span class="column-index">{{ column.column_index }}</span><span>{{ column.header }}</span><el-tag v-if="column.duplicate" type="warning" size="small">重复表头，按第 {{ column.column_index }} 列映射</el-tag></div>
          <el-select v-model="mappingSelections[column.column_index]" filterable clearable placeholder="搜索并选择商品主数据字段">
            <el-option v-for="field in TEMPLATE_MAPPING_FIELDS" :key="field.key" :label="field.label" :value="field.key" />
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
        <el-descriptions-item label="筛选方式">按数值硬条件，以及明确品牌、类目筛选；场景、用途、数量、库存、物流、有效期不参与筛选</el-descriptions-item>
        <el-descriptions-item label="筛选：协议价">{{ run.parsed_requirement.agreement_price_min ?? '不限' }} ～ {{ run.parsed_requirement.agreement_price_max ?? '不限' }}</el-descriptions-item>
        <el-descriptions-item label="筛选：京东价">{{ run.parsed_requirement.jd_price_min ?? '不限' }} ～ {{ run.parsed_requirement.jd_price_max ?? '不限' }}</el-descriptions-item>
        <el-descriptions-item label="筛选：折扣率 / 毛利率">{{ run.parsed_requirement.discount_rate_min ?? '不限' }} ～ {{ run.parsed_requirement.discount_rate_max ?? '不限' }} / {{ ratioValue(run.parsed_requirement.gross_margin_min, '不限') }} ～ {{ ratioValue(run.parsed_requirement.gross_margin_max, '不限') }}</el-descriptions-item>
        <el-descriptions-item label="筛选：指定品牌">{{ run.parsed_requirement.required_brands?.join('、') || '不限' }}</el-descriptions-item>
        <el-descriptions-item label="筛选：指定类目">{{ specifiedCategoryText() }}</el-descriptions-item>
        <el-descriptions-item v-if="run.category_catalog_snapshot" label="真实类目清单">本次已冻结 {{ run.category_catalog_snapshot.items.length }} 条商品库三级类目路径</el-descriptions-item>
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

    <el-card v-if="candidateTotal">
      <template #header><div class="card-header"><div><strong>候选商品与人工确认</strong><span class="muted">仅按硬条件筛选，评分取商品主数据；最终结果由人工确认。</span></div><div class="selection-actions"><el-button :disabled="!selectionEditable" @click="setCurrentPageSelected(true)">全选本页</el-button><el-button :disabled="!selectionEditable" @click="selectAllUnconfirmedCandidates">全选全部待确认商品</el-button><el-button :disabled="!selectionEditable" @click="resetCandidateSelection">清空选择</el-button><el-popover placement="bottom-end" :width="340" trigger="click"><template #reference><el-button :icon="Setting">自定义显示列</el-button></template><p class="column-picker-hint">商品图片、SKU、商品名称固定为前 3 列；其余列按勾选先后依次显示。</p><div class="column-picker"><el-checkbox v-for="option in RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS" :key="option.key" :model-value="isCandidateColumnSelected(option.key)" @change="(checked: unknown) => updateCandidateColumnSelection(option.key, checked)">{{ option.label }}</el-checkbox></div></el-popover><el-button v-if="auth.hasPermission('recommendation:review')" type="primary" :disabled="!selectionEditable || selectedCandidateCount === 0" :loading="acting" @click="confirmSelectedCandidates">批量确认选中（{{ selectedCandidateCount }}）</el-button></div></div></template>
      <el-table :data="run?.candidates ?? []">
        <el-table-column width="52"><template #header><el-checkbox :model-value="pageAllSelected" :indeterminate="pagePartiallySelected" :disabled="!selectionEditable || selectableOnPage.length === 0" @change="(value: string | number | boolean) => setCurrentPageSelected(Boolean(value))" /></template><template #default="{ row }"><el-checkbox :model-value="isCandidateSelected(row)" :disabled="!selectionEditable || Boolean(row.confirmation)" @change="(value: string | number | boolean) => setCandidateSelected(row, Boolean(value))" /></template></el-table-column>
        <el-table-column prop="rank" label="序号" width="70" fixed="left" />
        <el-table-column label="商品图片" width="108" fixed="left"><template #default="{ row }"><el-image v-if="candidateImageUrl(row)" class="candidate-image" :src="candidateImageUrl(row)" fit="contain" :preview-src-list="[candidateImageUrl(row)!]" preview-teleported /><div v-else class="image-placeholder">暂无图片</div></template></el-table-column>
        <el-table-column label="SKU" min-width="130" fixed="left"><template #default="{ row }">{{ productValue(row, 'sku') }}</template></el-table-column>
        <el-table-column label="商品名称" min-width="220" show-overflow-tooltip fixed="left"><template #default="{ row }">{{ productValue(row, 'product_name') }}</template></el-table-column>
        <el-table-column v-for="column in visibleCandidateColumns" :key="column.key" :label="column.label" :min-width="column.minWidth" show-overflow-tooltip><template #default="{ row }">{{ candidateColumnValue(row, column) }}</template></el-table-column>
        <el-table-column label="确认状态" width="120" fixed="right"><template #default="{ row }"><el-tag :type="row.confirmation ? 'success' : 'info'">{{ row.confirmation ? '已确认' : '待确认' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="110" fixed="right"><template #default="{ row }"><el-button v-if="auth.hasPermission('recommendation:review')" link type="primary" @click="openConfirmation(row)">{{ selectionEditable ? '确认选品' : '查看选品' }}</el-button></template></el-table-column>
      </el-table>
      <el-pagination v-model:current-page="candidatePage" v-model:page-size="candidatePageSize" :page-sizes="[50, 100, 200]" :total="candidateTotal" layout="total, sizes, prev, pager, next" @current-change="changeCandidatePage" @size-change="changeCandidatePageSize" />
    </el-card>

    <el-empty v-if="mappingConfirmed && !run" description="模板已确认，可以开始生成自由推品推荐" />

    <el-dialog v-model="confirmVisible" title="人工确认候选商品" width="min(640px, 92vw)">
      <el-form label-position="top" :disabled="!selectionEditable"><el-form-item label="活动价"><el-input v-model="confirmation.campaign_price" inputmode="decimal" /></el-form-item><el-form-item label="发货状态"><el-input v-model="confirmation.delivery_status" /></el-form-item><el-form-item label="库存状态"><el-input v-model="confirmation.inventory_status" /></el-form-item><el-form-item label="是否厂直"><el-select v-model="confirmation.factory_direct"><el-option label="待确认" value="PENDING" /><el-option label="是" value="YES" /><el-option label="否" value="NO" /></el-select></el-form-item><el-form-item label="履约说明"><el-input v-model="confirmation.fulfillment_cycle" type="textarea" :rows="3" /></el-form-item><el-form-item label="依据与备注"><el-input v-model="confirmation.evidence" type="textarea" :rows="3" /></el-form-item></el-form>
      <template #footer><el-button @click="confirmVisible = false">{{ selectionEditable ? '取消' : '关闭' }}</el-button><el-button v-if="selectionEditable" type="primary" :loading="acting" @click="saveConfirmation">确认保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.workspace { display: grid; gap: 18px; }.workspace header { display: flex; justify-content: space-between; gap: 20px; padding: 24px 28px; border-radius: 14px; background: linear-gradient(135deg, #edf5ff, #f2f8f5); }.workspace h1 { margin: 4px 0; }.workspace header p { margin: 0; color: #2670ca; font-weight: 700; }.actions, .card-header, .run-actions, .mapping-meta, .card-actions, .selection-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }.card-header { justify-content: space-between; }.mapping-tip { margin-bottom: 16px; }.mapping-meta { margin-bottom: 16px; }.mapping-meta .el-select { width: 280px; }.mapping-table { overflow: hidden; border: 1px solid #e4e7ed; border-radius: 8px; }.mapping-table-head, .mapping-row { display: grid; grid-template-columns: minmax(240px, 1fr) minmax(280px, 1fr); gap: 16px; align-items: center; padding: 10px 14px; }.mapping-table-head { background: #f5f7fa; color: #606266; font-weight: 600; }.mapping-row + .mapping-row { border-top: 1px solid #ebeef5; }.template-column { display: flex; align-items: center; gap: 10px; min-width: 0; }.column-index { display: inline-grid; place-items: center; width: 26px; height: 26px; flex: 0 0 auto; border-radius: 50%; background: #ecf5ff; color: #409eff; font-size: 12px; }.card-actions { justify-content: flex-end; margin-top: 16px; }.muted { color: #909399; font-size: 13px; }.el-progress + .muted { margin-bottom: 18px; }.el-pagination { justify-content: flex-end; margin-top: 16px; }
.column-picker { display: grid; grid-template-columns: 1fr 1fr; }.column-picker-hint { margin: 0 0 10px; color: var(--text-secondary); font-size: 12px; line-height: 1.5; }.candidate-image { width: 72px; height: 72px; }.image-placeholder { display: grid; place-items: center; width: 72px; height: 72px; color: #909399; background: #f5f7fa; border-radius: 4px; font-size: 12px; }
.supplement-box { display: grid; gap: 12px; margin-top: 18px; justify-items: start; }.supplement-box .el-textarea { width: 100%; }
@media (max-width: 767px) { .workspace header { flex-direction: column; }.mapping-table-head { display: none; }.mapping-row { grid-template-columns: 1fr; gap: 8px; } }
</style>
