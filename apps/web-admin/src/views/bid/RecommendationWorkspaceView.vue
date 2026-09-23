<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { ElMessage } from "element-plus"
import { useRoute, useRouter } from "vue-router"
import { bidApi } from "../../api/bid"
import { recommendationApi } from "../../api/recommendation"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type { BidProjectDetail } from "../../types/bid"
import {
  RUN_STATUS_LABELS,
  TEMPLATE_MAPPING_FIELDS,
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
const confirmVisible = ref(false)
const selectedCandidate = ref<RecommendationCandidate>()
const confirmation = reactive({ campaign_price: "", fulfillment: "", evidence: "" })
let pollTimer: ReturnType<typeof setInterval> | undefined

const mappingConfirmed = computed(() => Boolean(mapping.value?.confirmed_at))
const activeRun = computed(() => run.value && ["QUEUED", "ANALYZING", "RETRIEVING", "RANKING"].includes(run.value.status))
const canStart = computed(() => mappingConfirmed.value && !activeRun.value && auth.hasPermission("recommendation:run"))
const canExport = computed(() => run.value?.status === "CONFIRMED" && mappingConfirmed.value && auth.hasPermission("recommendation:export"))

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
      run.value = await recommendationApi.detail(projectId)
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
  acting.value = true
  try {
    run.value = await recommendationApi.start(projectId)
    ElMessage.success("自由推品任务已启动")
    syncPolling()
  } catch (error) {
    ElMessage.error(messageFor(error, "启动推荐任务失败"))
  } finally {
    acting.value = false
  }
}

async function refreshRun() {
  try {
    run.value = await recommendationApi.detail(projectId)
    syncPolling()
  } catch (error) {
    if (!(error instanceof HttpError && error.status === 404)) ElMessage.error(messageFor(error, "刷新推荐进度失败"))
  }
}

async function cancelRun() {
  if (!run.value) return
  acting.value = true
  try {
    run.value = await recommendationApi.cancel(run.value.id)
    ElMessage.success("已提交取消请求")
    syncPolling()
  } catch (error) {
    ElMessage.error(messageFor(error, "取消推荐任务失败"))
  } finally {
    acting.value = false
  }
}

function openConfirmation(candidate: RecommendationCandidate) {
  selectedCandidate.value = candidate
  confirmation.campaign_price = candidate.confirmation?.campaign_price ?? String(candidate.price_snapshot.campaign_price ?? "")
  confirmation.fulfillment = candidate.confirmation?.fulfillment ?? ""
  confirmation.evidence = candidate.confirmation?.evidence ?? ""
  confirmVisible.value = true
}

async function saveConfirmation() {
  if (!selectedCandidate.value) return
  acting.value = true
  try {
    run.value = await recommendationApi.confirm(selectedCandidate.value.id, {
      selected: true,
      campaign_price: confirmation.campaign_price || null,
      fulfillment: confirmation.fulfillment || null,
      evidence: confirmation.evidence || null,
    })
    confirmVisible.value = false
    ElMessage.success("人工确认已保存")
  } catch (error) {
    ElMessage.error(messageFor(error, "保存人工确认失败"))
  } finally {
    acting.value = false
  }
}

async function exportResult() {
  if (!run.value) return
  acting.value = true
  try {
    const blob = await recommendationApi.export(run.value.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = `${project.value?.project_name ?? "自由推品"}-推荐结果.xlsx`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success("推荐结果导出成功")
  } catch (error) {
    ElMessage.error(messageFor(error, "导出推荐结果失败"))
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
      <div class="actions"><el-button @click="router.push('/bid-projects')">返回项目</el-button><el-button v-if="activeRun" :loading="acting" @click="cancelRun">取消任务</el-button><el-button type="primary" :disabled="!canStart" :loading="acting" @click="startRun">{{ run ? "重新生成推荐" : "开始生成推荐" }}</el-button><el-button type="success" :disabled="!canExport" :loading="acting" @click="exportResult">导出确认结果</el-button></div>
    </header>

    <el-alert v-if="!mappingConfirmed" title="开始推荐前必须人工确认本项目模板的字段映射。毛利、厂直和物流等歧义字段不会由系统自动猜测。" type="warning" :closable="false" />
    <el-card v-if="mapping">
      <template #header><div class="card-header"><strong>结果模板字段映射</strong><el-tag :type="mappingConfirmed ? 'success' : 'warning'">{{ mappingConfirmed ? "已确认" : "待确认" }}</el-tag></div></template>
      <div class="mapping-meta"><el-input v-model="mapping.sheet_name"><template #prepend>工作表</template></el-input><el-input-number v-model="mapping.header_row" :min="1" controls-position="right" /><span>表头行</span><el-input-number v-model="mapping.data_start_row" :min="2" controls-position="right" /><span>数据起始行</span></div>
      <div class="mapping-grid"><el-input v-for="field in TEMPLATE_MAPPING_FIELDS" :key="field.key" v-model="mapping.mapping_json[field.key]" clearable :placeholder="`模板中的${field.label}列名`"><template #prepend>{{ field.label }}</template></el-input></div>
      <div class="card-actions"><el-button v-if="auth.hasPermission('recommendation:create')" type="primary" :loading="acting" @click="saveMapping">确认字段映射</el-button></div>
    </el-card>

    <el-card v-if="run">
      <template #header><div class="card-header"><strong>Agent 运行状态</strong><el-tag>{{ RUN_STATUS_LABELS[run.status] }}</el-tag></div></template>
      <el-progress :percentage="run.progress_percent ?? (activeRun ? 50 : 100)" :status="run.status === 'FAILED' ? 'exception' : undefined" />
      <p class="muted">{{ run.progress_message ?? run.error ?? `模型：${run.provider ?? '-'} / ${run.model ?? '-'}` }}</p>
      <el-descriptions v-if="run.parsed_requirement" title="需求理解" :column="2" border>
        <el-descriptions-item label="需求摘要" :span="2">{{ run.parsed_requirement.summary }}</el-descriptions-item>
        <el-descriptions-item label="关键词">{{ run.parsed_requirement.keywords.join('、') }}</el-descriptions-item>
        <el-descriptions-item label="场景">{{ run.parsed_requirement.scenarios.join('、') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="偏好品牌">{{ run.parsed_requirement.preferred_brands.join('、') || '-' }}</el-descriptions-item>
        <el-descriptions-item label="预算">{{ run.parsed_requirement.budget_min ?? '不限' }} ～ {{ run.parsed_requirement.budget_max ?? '不限' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card v-if="run?.category_choices.length">
      <template #header><strong>推荐类目方向</strong></template>
      <div class="category-grid"><div v-for="choice in run.category_choices" :key="choice.id" class="category-card"><strong>{{ [choice.level1_name, choice.level2_name, choice.level3_name].filter(Boolean).join(' / ') }}</strong><span>{{ choice.reason }}</span><el-tag size="small">{{ choice.candidate_count }} 个候选</el-tag></div></div>
    </el-card>

    <el-card v-if="run?.candidates.length">
      <template #header><div class="card-header"><strong>候选商品与人工确认</strong><span class="muted">Agent 只提供排序建议，最终价格与履约信息由人工确认。</span></div></template>
      <el-table :data="run.candidates">
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
      <el-form label-position="top"><el-form-item label="活动价"><el-input v-model="confirmation.campaign_price" inputmode="decimal" /></el-form-item><el-form-item label="履约说明"><el-input v-model="confirmation.fulfillment" type="textarea" :rows="3" /></el-form-item><el-form-item label="依据与备注"><el-input v-model="confirmation.evidence" type="textarea" :rows="3" /></el-form-item></el-form>
      <template #footer><el-button @click="confirmVisible = false">取消</el-button><el-button type="primary" :loading="acting" @click="saveConfirmation">确认保存</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.workspace { display: grid; gap: 18px; }.workspace header { display: flex; justify-content: space-between; gap: 20px; padding: 24px 28px; border-radius: 14px; background: linear-gradient(135deg, #edf5ff, #f2f8f5); }.workspace h1 { margin: 4px 0; }.workspace header p { margin: 0; color: #2670ca; font-weight: 700; }.actions, .card-header, .mapping-meta, .card-actions { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }.card-header { justify-content: space-between; }.mapping-meta { margin-bottom: 16px; }.mapping-meta .el-input { width: 280px; }.mapping-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }.card-actions { justify-content: flex-end; margin-top: 16px; }.category-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; }.category-card { display: grid; gap: 10px; padding: 16px; border: 1px solid #e4e7ed; border-radius: 10px; }.muted { color: #909399; font-size: 13px; }.el-progress + .muted { margin-bottom: 18px; }
@media (max-width: 767px) { .workspace header { flex-direction: column; }.mapping-grid { grid-template-columns: 1fr; } }
</style>
