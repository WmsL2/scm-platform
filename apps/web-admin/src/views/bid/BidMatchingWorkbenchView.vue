<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useRoute, useRouter } from "vue-router"
import { bidApi } from "../../api/bid"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import { useWorkspaceStore } from "../../stores/workspace"
import { ITEM_STATUS_LABELS, NO_QUOTE_REASON_LABELS, PROJECT_STATUS_LABELS, type BidCandidate, type BidItemStatus, type BidProjectDetail, type BidProjectItem, type NoQuoteReason } from "../../types/bid"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const workspace = useWorkspaceStore()
const id = String(route.params.id)
const project = ref<BidProjectDetail>()
const rows = ref<BidProjectItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const loading = ref(false)
const acting = ref(false)
const filters = reactive({ keyword: "", status: undefined as BidItemStatus | undefined })
const drawer = ref(false)
const candidates = ref<BidCandidate[]>([])
const candidateLoading = ref(false)
const item = ref<BidProjectItem>()
const priceVisible = ref(false)
const candidate = ref<BidCandidate>()
const price = ref("")
const note = ref("")
const noQuoteVisible = ref(false)
const noQuote = reactive({ reason: "NO_PRODUCT_MATCH" as NoQuoteReason, reason_detail: "" })

const isType1 = computed(() => project.value?.recommendation_type === "TYPE_1_SPECIFICATION")
const isType2 = computed(() => project.value?.recommendation_type === "TYPE_2_IDENTIFIED_PRODUCT")
const workspaceTitle = computed(() => isType2.value ? "指定商品比价" : "规格参数匹配")
const workspaceCode = computed(() => isType2.value ? "IDENTIFIED PRODUCT" : "SPECIFICATION MATCHING")
const terminal = computed(() => ["WON", "LOST", "VOIDED"].includes(project.value?.status ?? ""))
const canStartMatching = computed(() => {
  const status = project.value?.status ?? ""
  return project.value?.import_status === "PARSED"
    && auth.hasPermission("bid:match")
    && (status === "IMPORTED" || (isType2.value && status === "SELECTING"))
})
const canExport = computed(() => auth.hasPermission("bid:export") && ["READY", "EXPORTED"].includes(project.value?.status ?? ""))

function messageFor(error: unknown, fallback: string): string {
  return error instanceof HttpError ? error.response.message : fallback
}

function canSelect(row: BidProjectItem): boolean {
  return isType1.value && auth.hasPermission("bid:select") && !terminal.value
    && ["SELECTING", "READY", "EXPORTED"].includes(project.value?.status ?? "")
    && row.status !== "PENDING"
}

function snapshot(selection: BidProjectItem["current_selection"], key: "product_snapshot" | "supplier_snapshot") {
  return selection?.[key] ?? {}
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const [detail, result] = await Promise.all([
      bidApi.get(id),
      bidApi.items(id, { page: page.value, page_size: pageSize.value, status: filters.status, keyword: filters.keyword.trim() || undefined }),
    ])
    project.value = detail
    rows.value = result.items
    total.value = result.total
    page.value = result.page
    if (route.meta) route.meta.title = workspaceTitle.value
    workspace.renameRoute(route.fullPath, workspaceTitle.value)
  } catch (error) {
    ElMessage.error(messageFor(error, "加载匹配结果失败"))
  } finally {
    loading.value = false
  }
}

async function startMatching(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      isType2.value ? "将按 SKU 或品牌型号精确匹配，并自动选择最低有效报价。" : "将按需求规格和限价生成商品候选。",
      isType2.value ? "执行指定商品比价" : "执行规格参数匹配",
    )
    acting.value = true
    await bidApi.startMatching(id)
    ElMessage.success(isType2.value ? "指定商品比价完成" : "规格参数匹配完成")
    await load()
  } catch (error) {
    if (error !== "cancel" && error !== "close") ElMessage.error(messageFor(error, "自动匹配失败"))
  } finally {
    acting.value = false
  }
}

async function openCandidates(row: BidProjectItem): Promise<void> {
  item.value = row
  drawer.value = true
  candidateLoading.value = true
  try {
    candidates.value = await bidApi.candidates(id, row.id)
  } catch (error) {
    ElMessage.error(messageFor(error, "加载候选失败"))
  } finally {
    candidateLoading.value = false
  }
}

function pick(value: BidCandidate): void {
  candidate.value = value
  price.value = value.cost_price ?? value.agreement_price ?? ""
  note.value = ""
  priceVisible.value = true
}

async function selectCandidate(): Promise<void> {
  if (!item.value || !candidate.value || !/^\d+(\.\d+)?$/.test(price.value) || Number(price.value) <= 0) {
    ElMessage.error("请输入大于 0 的选品单价")
    return
  }
  if (item.value.max_price && Number(price.value) > Number(item.value.max_price)) {
    ElMessage.error("选品单价不能高于需求限价")
    return
  }
  acting.value = true
  try {
    await bidApi.select(id, item.value.id, { candidate_id: candidate.value.candidate_id, selected_unit_price: price.value, note: note.value })
    priceVisible.value = false
    drawer.value = false
    ElMessage.success("选品已保存")
    await load()
  } catch (error) {
    ElMessage.error(messageFor(error, "选品失败"))
  } finally {
    acting.value = false
  }
}

function openNoQuote(row: BidProjectItem): void {
  item.value = row
  noQuote.reason = "NO_PRODUCT_MATCH"
  noQuote.reason_detail = ""
  noQuoteVisible.value = true
}

async function markNoQuote(): Promise<void> {
  if (!item.value) return
  if (noQuote.reason === "OTHER" && !noQuote.reason_detail.trim()) {
    ElMessage.error("其他原因必须填写说明")
    return
  }
  acting.value = true
  try {
    await bidApi.noQuote(id, item.value.id, noQuote)
    noQuoteVisible.value = false
    ElMessage.success("已标记无法报价")
    await load()
  } catch (error) {
    ElMessage.error(messageFor(error, "操作失败"))
  } finally {
    acting.value = false
  }
}

async function exportResult(): Promise<void> {
  acting.value = true
  try {
    const file = await bidApi.export(id)
    const blob = await bidApi.download(id, file.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = file.original_filename
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success("回填结果已导出")
    await load()
  } catch (error) {
    ElMessage.error(messageFor(error, "导出失败"))
  } finally {
    acting.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="workbench" v-loading="loading">
    <header class="workbench-header">
      <div><p>{{ workspaceCode }}</p><h1>{{ project?.project_name ?? workspaceTitle }}</h1><span v-if="project">{{ project.project_code }} · {{ workspaceTitle }} · {{ PROJECT_STATUS_LABELS[project.status] }}</span></div>
      <div class="header-actions">
        <el-button @click="router.push('/bid-projects')">返回项目列表</el-button>
        <el-button v-if="canStartMatching" type="primary" :loading="acting" @click="startMatching">{{ isType2 ? "执行最低价匹配" : "开始规格匹配" }}</el-button>
        <el-button v-if="canExport" type="success" :loading="acting" @click="exportResult">导出回填表</el-button>
      </div>
    </header>

    <el-alert v-if="project && project.import_status !== 'PARSED'" :title="project.import_error ?? '客户需求文件尚未完成解析，暂时不能开始。'" type="warning" :closable="false" />
    <el-alert v-else-if="project?.status === 'IMPORTED'" :title="isType2 ? '客户需求已解析。请确认后点击“执行最低价匹配”。' : '客户需求已解析。请确认后点击“开始规格匹配”。'" type="info" :closable="false" />
    <el-alert v-else-if="isType2" title="系统只按 SKU 或品牌型号精确匹配，自动选择当前成本价最低且不超过限价的商品；没有商品则显示未匹配。" type="success" :closable="false" />
    <el-alert v-else-if="isType1" title="系统已按规格参数生成候选。请只处理需要确认的候选或无法报价项，全部处理后可直接导出回填表。" type="info" :closable="false" />
    <el-alert v-else title="该工作台仅用于类型 1、2。" type="warning" :closable="false" />

    <el-card>
      <el-form inline class="filter-form" @submit.prevent="page = 1; load()">
        <el-form-item><el-input v-model="filters.keyword" clearable placeholder="搜索商品、品牌、型号或客户编码" @change="page = 1; load()" /></el-form-item>
        <el-form-item><el-select v-model="filters.status" clearable placeholder="全部状态" @change="page = 1; load()"><el-option v-for="(label, key) in ITEM_STATUS_LABELS" :key="key" :label="label" :value="key" /></el-select></el-form-item>
        <el-form-item><el-button type="primary" @click="page = 1; load()">查询</el-button></el-form-item>
      </el-form>
      <el-table :data="rows" max-height="620">
        <el-table-column prop="source_row_number" label="Excel 行号" width="95" />
        <el-table-column prop="buyer_item_code" label="客户商品编码" min-width="130" />
        <el-table-column prop="product_name" label="商品名称" min-width="150" />
        <el-table-column prop="brand" label="品牌" />
        <el-table-column prop="model" label="型号" min-width="120" />
        <el-table-column prop="specification" label="规格" min-width="160" />
        <el-table-column prop="max_price" label="最高限价" />
        <el-table-column label="匹配状态"><template #default="{ row }"><el-tag>{{ ITEM_STATUS_LABELS[row.status] }}</el-tag></template></el-table-column>
        <el-table-column label="匹配商品" min-width="190"><template #default="{ row }"><template v-if="row.current_selection"><div>{{ snapshot(row.current_selection, "product_snapshot").product_name }}</div><small>{{ snapshot(row.current_selection, "product_snapshot").brand }} {{ snapshot(row.current_selection, "product_snapshot").model }}</small></template><span v-else>—</span></template></el-table-column>
        <el-table-column label="供应商" min-width="170"><template #default="{ row }"><template v-if="row.current_selection">{{ snapshot(row.current_selection, "supplier_snapshot").supplier_name }}</template><span v-else>—</span></template></el-table-column>
        <el-table-column :label="isType2 ? '最低报价' : '选中单价'"><template #default="{ row }">{{ row.current_selection?.selected_unit_price ?? "—" }}</template></el-table-column>
        <el-table-column v-if="isType1" label="处理" fixed="right" width="150"><template #default="{ row }"><el-button v-if="canSelect(row) && ['UNIQUE_MATCH', 'MULTIPLE_MATCH', 'SELECTED'].includes(row.status)" link type="primary" @click="openCandidates(row)">{{ row.status === "SELECTED" ? "重新选择" : "选择商品" }}</el-button><el-button v-if="canSelect(row)" link type="warning" @click="openNoQuote(row)">无法报价</el-button></template></el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @current-change="load" @size-change="page = 1; load()" />
    </el-card>

    <el-drawer v-model="drawer" title="匹配候选商品" size="min(920px, 95vw)">
      <el-table v-loading="candidateLoading" :data="candidates">
        <el-table-column prop="rank" label="排名" width="70" /><el-table-column prop="product_name" label="商品" min-width="180" /><el-table-column prop="brand" label="品牌" /><el-table-column prop="model" label="型号" />
        <el-table-column label="供应商" min-width="160"><template #default="{ row }">{{ row.supplier_name }}</template></el-table-column><el-table-column prop="cost_price" label="当前报价" />
        <el-table-column label="操作" width="90"><template #default="{ row }"><el-button link type="primary" @click="pick(row)">选择</el-button></template></el-table-column>
      </el-table>
    </el-drawer>

    <el-dialog v-model="priceVisible" title="确认商品与报价" width="min(560px, 92vw)"><p v-if="candidate">{{ candidate.product_name }} · {{ candidate.supplier_name }}</p><el-input v-model="price" placeholder="选品单价" /><el-input v-model="note" type="textarea" :rows="3" placeholder="备注（可选）" /><template #footer><el-button @click="priceVisible = false">取消</el-button><el-button type="primary" :loading="acting" @click="selectCandidate">确认</el-button></template></el-dialog>
    <el-dialog v-model="noQuoteVisible" title="标记无法报价" width="min(520px, 92vw)"><el-select v-model="noQuote.reason"><el-option v-for="(label, key) in NO_QUOTE_REASON_LABELS" :key="key" :label="label" :value="key" /></el-select><el-input v-if="noQuote.reason === 'OTHER'" v-model="noQuote.reason_detail" type="textarea" :rows="3" placeholder="请填写说明" /><template #footer><el-button @click="noQuoteVisible = false">取消</el-button><el-button type="warning" :loading="acting" @click="markNoQuote">确认</el-button></template></el-dialog>
  </div>
</template>

<style scoped>
.workbench { display: grid; gap: 18px; }
.workbench-header { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 24px 28px; border-radius: 14px; background: linear-gradient(135deg, #edf5ff, #f2f8f5); }
.workbench-header p { margin: 0; color: #2670ca; font-weight: 700; }
.workbench-header h1 { margin: 4px 0; }
.workbench-header span, small { color: #6b7280; }
.header-actions { display: flex; flex-wrap: wrap; gap: 10px; }
.filter-form { margin-bottom: 4px; }
.filter-form .el-input { width: 320px; }
.filter-form .el-select { width: 180px; }
.el-pagination { justify-content: flex-end; margin-top: 16px; }
.el-dialog .el-input, .el-dialog .el-select { width: 100%; margin-top: 12px; }
@media (max-width: 800px) { .workbench-header { align-items: flex-start; flex-direction: column; } .filter-form .el-input, .filter-form .el-select { width: 100%; } }
</style>
