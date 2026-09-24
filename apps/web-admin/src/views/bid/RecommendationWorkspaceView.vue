<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
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
  type RecommendationTemplateMapping,
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
const run = ref<RecommendationRun | null>(null)
const runHistory = ref<RecommendationRun[]>([])
const selectedCandidates = ref<RecommendationCandidate[]>([])
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
const canStart = computed(() => mappingConfirmed.value && !activeRun.value && auth.hasPermission("recommendation:run"))
const canExport = computed(() => Boolean(
  run.value
  && ["CONFIRMED", "EXPORTED"].includes(run.value.status)
  && run.value.candidates.some((item) => item.confirmation)
  && auth.hasPermission("recommendation:export"),
))
const resultStatuses = new Set(["CANDIDATES_READY", "WAITING_CONFIRMATION", "CONFIRMED", "EXPORTED"])

async function load() {
  loading.value = true
  try {
    project.value = await bidApi.get(projectId)
    if (project.value.project_type !== "FREE_RECOMMENDATION") {
      ElMessage.warning("该项目不是类型4自由推品项目")
      await router.replace(`/bid-projects/${projectId}`)
      return
    }
    templates.value = await bidApi.recommendationTemplates(projectId)
    const latest = templates.value.at(-1)
    if (latest) mapping.value = await bidApi.recommendationTemplateMapping(projectId, latest.id)
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
      mapping_json: Object.fromEntries(Object.entries(mapping.value.mapping_json).filter(([, value]) => value.trim())),
    })
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

function handleCandidateSelection(rows: RecommendationCandidate[]) {
  selectedCandidates.value = rows.filter((item) => !item.confirmation)
}

function canSelectCandidate(candidate: RecommendationCandidate): boolean {
  return !candidate.confirmation
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

function productValue(candidate: RecommendationCandidate, key: string): string {
  const value = candidate.product_snapshot[key] ?? candidate.price_snapshot[key]
  return value === null || value === undefined || value === "" ? "-" : String(value)
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
      <div class="actions"><el-button @click="router.push('/bid-projects')">返回项目</el-button><el-button type="primary" :disabled="!canStart" :loading="acting" @click="startRun">{{ run ? "重新生成推荐" : "开始生成推荐" }}</el-button><el-button type="success" :disabled="!canExport" :loading="acting" @click="exportConfirmedCandidates">导出确认结果</el-button></div>
    </header>

    <el-alert v-if="!mappingConfirmed" title="开始推荐前必须人工确认本项目模板的字段映射。毛利、厂直和物流等歧义字段不会由系统自动猜测。" type="warning" :closable="false" />
    <el-card v-if="mapping">
      <template #header><div class="card-header"><strong>结果模板字段映射</strong><el-tag :type="mappingConfirmed ? 'success' : 'warning'">{{ mappingConfirmed ? "已确认" : "待确认" }}</el-tag></div></template>
      <div class="mapping-meta"><el-input v-model="mapping.sheet_name"><template #prepend>工作表</template></el-input><el-input-number v-model="mapping.header_row" :min="1" controls-position="right" /><span>表头行</span><el-input-number v-model="mapping.data_start_row" :min="2" controls-position="right" /><span>数据起始行</span></div>
      <div class="mapping-grid"><el-input v-for="field in TEMPLATE_MAPPING_FIELDS" :key="field.key" v-model="mapping.mapping_json[field.key]" clearable :placeholder="`模板中的${field.label}列名`"><template #prepend>{{ field.label }}</template></el-input></div>
      <div class="card-actions"><el-button v-if="auth.hasPermission('recommendation:create')" type="primary" :loading="acting" @click="saveMapping">确认字段映射</el-button></div>
    </el-card>

    <el-card v-if="run">
      <template #header><div class="card-header"><strong>Agent 运行状态</strong><div class="run-actions"><el-select :model-value="run.id" style="width: 260px" @change="switchRun"><el-option v-for="item in runHistory" :key="item.id" :label="`${new Date(item.created_at).toLocaleString()} · ${RUN_STATUS_LABELS[item.status]}`" :value="item.id" /></el-select><el-tag>{{ RUN_STATUS_LABELS[run.status] }}</el-tag></div></div></template>
      <el-progress :percentage="run.progress_percent ?? (activeRun ? 50 : 100)" :status="run.status === 'FAILED' ? 'exception' : undefined" />
      <p class="muted">{{ run.progress_message ?? run.error ?? `模型：${run.provider ?? '-'} / ${run.model ?? '-'}` }}</p>
      <el-descriptions v-if="run.parsed_requirement" title="需求理解" :column="2" border>
        <el-descriptions-item label="本次读取的需求" :span="2">{{ run.raw_requirement_snapshot }}</el-descriptions-item>
        <el-descriptions-item label="类目关键词">{{ run.parsed_requirement.category_keywords.join('、') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="场景关键词">{{ run.parsed_requirement.scenario_keywords.join('、') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="偏好品牌">{{ run.parsed_requirement.brand_keywords.join('、') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="京东价范围">{{ run.parsed_requirement.jd_price_min ?? '不限' }} ～ {{ run.parsed_requirement.jd_price_max ?? '不限' }}</el-descriptions-item>
        <el-descriptions-item label="最低毛利率">{{ run.parsed_requirement.gross_margin_min ?? '-' }}</el-descriptions-item>
        <el-descriptions-item label="履约方式">{{ run.parsed_requirement.fulfillment_mode ?? '-' }}</el-descriptions-item>
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

    <el-card v-if="run?.candidates.length">
      <template #header><div class="card-header"><div><strong>候选商品与人工确认</strong><span class="muted"> Agent 只提供排序建议，最终结果由人工确认。</span></div><el-button type="primary" :disabled="selectedCandidates.length === 0" :loading="acting" @click="confirmSelectedCandidates">批量确认选中（{{ selectedCandidates.length }}）</el-button></div></template>
      <el-table :data="run.candidates" @selection-change="handleCandidateSelection">
        <el-table-column type="selection" width="48" :selectable="canSelectCandidate" />
        <el-table-column prop="rank" label="排名" width="70" />
        <el-table-column label="商品" min-width="220"><template #default="{ row }"><strong>{{ productValue(row, 'product_name') }}</strong><div class="muted">{{ productValue(row, 'brand') }} / {{ productValue(row, 'model') }}</div></template></el-table-column>
        <el-table-column label="协议价"><template #default="{ row }">¥ {{ productValue(row, 'agreement_price') }}</template></el-table-column>
        <el-table-column label="毛利率"><template #default="{ row }">{{ productValue(row, 'gross_margin') }}</template></el-table-column>
        <el-table-column prop="score" label="推荐分" width="90" />
        <el-table-column prop="reason" label="推荐理由" min-width="260" />
        <el-table-column label="人工状态" width="110"><template #default="{ row }"><el-tag :type="row.confirmation ? 'success' : 'info'">{{ row.confirmation ? '已确认' : '待确认' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="110"><template #default="{ row }"><el-button v-if="auth.hasPermission('recommendation:review')" link type="primary" @click="openConfirmation(row)">确认选品</el-button></template></el-table-column>
      </el-table>
    </el-card>

    <el-empty v-if="mappingConfirmed && !run" description="模板已确认，可以开始生成自由推品推荐" />

    <el-dialog v-model="confirmVisible" title="人工确认候选商品" width="min(640px, 92vw)">
      <el-form label-position="top"><el-form-item label="活动价"><el-input v-model="confirmation.campaign_price" inputmode="decimal" /></el-form-item><el-form-item label="发货状态"><el-input v-model="confirmation.delivery_status" /></el-form-item><el-form-item label="库存状态"><el-input v-model="confirmation.inventory_status" /></el-form-item><el-form-item label="是否厂直"><el-select v-model="confirmation.factory_direct"><el-option label="待确认" value="PENDING" /><el-option label="是" value="YES" /><el-option label="否" value="NO" /></el-select></el-form-item><el-form-item label="履约说明"><el-input v-model="confirmation.fulfillment_cycle" type="textarea" :rows="3" /></el-form-item><el-form-item label="依据与备注"><el-input v-model="confirmation.evidence" type="textarea" :rows="3" /></el-form-item></el-form>
      <template #footer><el-button @click="confirmVisible = false">取消</el-button><el-button type="primary" :loading="acting" @click="saveConfirmation">确认保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.workspace { display: grid; gap: 18px; }.workspace header { display: flex; justify-content: space-between; gap: 20px; padding: 24px 28px; border-radius: 14px; background: linear-gradient(135deg, #edf5ff, #f2f8f5); }.workspace h1 { margin: 4px 0; }.workspace header p { margin: 0; color: #2670ca; font-weight: 700; }.actions, .card-header, .run-actions, .mapping-meta, .card-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }.card-header { justify-content: space-between; }.mapping-meta { margin-bottom: 16px; }.mapping-meta .el-input { width: 280px; }.mapping-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }.card-actions { justify-content: flex-end; margin-top: 16px; }.category-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; }.category-card { display: grid; gap: 10px; padding: 16px; border: 1px solid #e4e7ed; border-radius: 10px; }.muted { color: #909399; font-size: 13px; }.el-progress + .muted { margin-bottom: 18px; }
.supplement-box { display: grid; gap: 12px; margin-top: 18px; justify-items: start; }.supplement-box .el-textarea { width: 100%; }
@media (max-width: 767px) { .workspace header { flex-direction: column; }.mapping-grid { grid-template-columns: 1fr; } }
</style>
