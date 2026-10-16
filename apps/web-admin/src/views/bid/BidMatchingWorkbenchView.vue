<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useRoute, useRouter } from "vue-router"
import { bidApi } from "../../api/bid"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import { useWorkspaceStore } from "../../stores/workspace"
import { ITEM_STATUS_LABELS, NO_QUOTE_REASON_LABELS, PROJECT_STATUS_LABELS, type BidCandidate, type BidInputMapping, type BidItemStatus, type BidOutputMapping, type BidProjectDetail, type BidProjectItem, type NoQuoteReason } from "../../types/bid"
import RecommendationProductScopeForm from "./RecommendationProductScopeForm.vue"

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
const outputMapping = ref<BidOutputMapping>()
const outputMappingSelections = reactive<Record<string, string | null>>({})
const outputMappingHeaders = ref<string[]>([])
const additionalOutputHeader = ref<string>()
const mappingSaving = ref(false)
const inputMapping = ref<BidInputMapping>()
const inputMappingSelections = reactive<Record<string, string | null>>({})
const inputSheetName = ref("")
const inputHeaderRow = ref(1)
const inputDataStartRow = ref(2)
const inputMappingSaving = ref(false)
const inputStructureLoading = ref(false)
const mappingTab = ref<"input" | "output">("input")
const mappingTabInitialized = ref(false)

const isType1 = computed(() => project.value?.recommendation_type === "TYPE_1_SPECIFICATION")
const isType2 = computed(() => project.value?.recommendation_type === "TYPE_2_IDENTIFIED_PRODUCT")
const workspaceTitle = computed(() => isType2.value ? "指定商品比价" : "规格参数匹配")
const workspaceCode = computed(() => isType2.value ? "IDENTIFIED PRODUCT" : "SPECIFICATION MATCHING")
const terminal = computed(() => ["WON", "LOST", "VOIDED"].includes(project.value?.status ?? ""))
const canStartMatching = computed(() => {
  const status = project.value?.status ?? ""
  return project.value?.import_status === "PARSED"
    && outputMapping.value?.confirmed === true
    && auth.hasPermission("bid:match")
    && (status === "IMPORTED" || ((isType1.value || isType2.value) && ["SELECTING", "READY"].includes(status)))
})
const canExport = computed(() => outputMapping.value?.confirmed === true && auth.hasPermission("bid:export") && ["READY", "EXPORTED"].includes(project.value?.status ?? ""))

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

function applyInputMapping(value: BidInputMapping): void {
  inputMapping.value = value
  inputSheetName.value = value.sheet_name
  inputHeaderRow.value = value.header_row
  inputDataStartRow.value = value.data_start_row
  Object.keys(inputMappingSelections).forEach((key) => delete inputMappingSelections[key])
  value.headers.forEach((header) => { inputMappingSelections[header] = null })
  Object.entries(value.mapping).forEach(([fieldKey, header]) => {
    if (Object.hasOwn(inputMappingSelections, header)) inputMappingSelections[header] = fieldKey
  })
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
    const supportsMapping = ["TYPE_1_SPECIFICATION", "TYPE_2_IDENTIFIED_PRODUCT"].includes(detail.recommendation_type ?? "")
    if (supportsMapping && detail.template_id) {
      applyInputMapping(await bidApi.inputMapping(id))
    } else {
      inputMapping.value = undefined
    }
    if (detail.import_status === "PARSED" && supportsMapping) {
      outputMapping.value = await bidApi.outputMapping(id)
      Object.keys(outputMappingSelections).forEach((key) => delete outputMappingSelections[key])
      outputMappingHeaders.value = [...outputMapping.value.suggested_headers]
      Object.values(outputMapping.value.mapping).forEach((header) => {
        if (!outputMappingHeaders.value.includes(header)) outputMappingHeaders.value.push(header)
      })
      outputMappingHeaders.value.forEach((header) => { outputMappingSelections[header] = null })
      Object.entries(outputMapping.value.mapping).forEach(([fieldKey, header]) => {
        if (Object.hasOwn(outputMappingSelections, header)) outputMappingSelections[header] = fieldKey
      })
    } else {
      outputMapping.value = undefined
    }
    if (!mappingTabInitialized.value) {
      mappingTab.value = detail.import_status === "PARSED" ? "output" : "input"
      mappingTabInitialized.value = true
    }
    if (route.meta) route.meta.title = workspaceTitle.value
    workspace.renameRoute(route.fullPath, workspaceTitle.value)
  } catch (error) {
    ElMessage.error(messageFor(error, "加载匹配结果失败"))
  } finally {
    loading.value = false
  }
}

async function refreshInputStructure(): Promise<void> {
  if (!inputSheetName.value || inputHeaderRow.value < 1) return
  inputStructureLoading.value = true
  try {
    const value = await bidApi.inputMapping(id, { sheet_name: inputSheetName.value, header_row: inputHeaderRow.value })
    applyInputMapping(value)
  } catch (error) {
    ElMessage.error(messageFor(error, "读取所选表头失败"))
  } finally {
    inputStructureLoading.value = false
  }
}

async function confirmInputMapping(): Promise<void> {
  if (!inputMapping.value) return
  const selectedFields = Object.values(inputMappingSelections).filter((value): value is string => Boolean(value))
  if (new Set(selectedFields).size !== selectedFields.length) {
    ElMessage.error("同一个需求字段只能对应一个客户表列")
    return
  }
  const mapping = Object.fromEntries(
    Object.entries(inputMappingSelections)
      .filter((entry): entry is [string, string] => Boolean(entry[1]))
      .map(([header, fieldKey]) => [fieldKey, header]),
  )
  inputMappingSaving.value = true
  try {
    await bidApi.confirmInputMapping(id, {
      sheet_name: inputSheetName.value,
      header_row: inputHeaderRow.value,
      data_start_row: inputDataStartRow.value,
      mapping,
    })
    ElMessage.success("需求字段映射已确认，客户需求行解析完成")
    await load()
    mappingTab.value = "output"
  } catch (error) {
    ElMessage.error(messageFor(error, "确认需求字段映射失败"))
  } finally {
    inputMappingSaving.value = false
  }
}

function addOutputHeader(): void {
  const header = additionalOutputHeader.value
  if (!header || outputMappingHeaders.value.includes(header)) return
  outputMappingHeaders.value.push(header)
  outputMappingSelections[header] = null
  additionalOutputHeader.value = undefined
}

function removeOutputHeader(header: string): void {
  outputMappingHeaders.value = outputMappingHeaders.value.filter((value) => value !== header)
  delete outputMappingSelections[header]
}

async function confirmOutputMapping(): Promise<void> {
  if (!outputMapping.value) return
  const selectedFields = Object.values(outputMappingSelections).filter((value): value is string => Boolean(value))
  if (new Set(selectedFields).size !== selectedFields.length) {
    ElMessage.error("同一个商品大表／报价结果字段只能映射一个客户原表列")
    return
  }
  const mapping = Object.fromEntries(
    Object.entries(outputMappingSelections)
      .filter((entry): entry is [string, string] => Boolean(entry[1]))
      .map(([header, fieldKey]) => [fieldKey, header]),
  )
  mappingSaving.value = true
  try {
    outputMapping.value = await bidApi.updateOutputMapping(id, mapping)
    ElMessage.success("回填字段映射已确认，不会改变商品匹配条件")
  } catch (error) {
    ElMessage.error(messageFor(error, "保存回填字段映射失败"))
  } finally {
    mappingSaving.value = false
  }
}

async function startMatching(): Promise<void> {
  try {
    await ElMessageBox.confirm(
      isType2.value ? "系统先按客户 SKU 或品牌+型号匹配，再由 AI 复核颜色、适用机型、容量、包装和备注等附加条件。" : "将按需求规格和限价生成商品候选。",
      isType2.value ? "执行指定商品比价" : "执行规格参数匹配",
    )
    acting.value = true
    const result = await bidApi.startMatching(id)
    if (result.candidate_product_count === 0) ElMessage.warning("当前商品范围内没有可用于匹配的合格商品")
    else if (result.matched_item_count === 0) ElMessage.warning("当前商品范围内有合格商品，但没有与本次客户需求匹配的结果")
    else ElMessage.success(isType2.value ? "指定商品比价完成" : "规格参数匹配完成")
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
  price.value = value.agreement_price ?? ""
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
        <el-button v-if="canStartMatching" type="primary" :loading="acting" @click="startMatching">{{ isType2 ? "执行 AI 同品比价" : "开始规格匹配" }}</el-button>
        <el-button v-if="canExport" type="success" :loading="acting" @click="exportResult">导出回填表</el-button>
      </div>
    </header>

    <el-card v-if="['IMPORTED', 'SELECTING', 'READY'].includes(project?.status ?? '')" class="scope-card"><RecommendationProductScopeForm :project="project" :disabled="acting || !auth.hasPermission('bid:update')" @updated="project = $event" /></el-card>

    <el-alert v-if="project && project.import_status !== 'PARSED'" :title="project.import_error ?? '请先人工确认 AI 预识别的客户需求字段。'" type="warning" :closable="false" />
    <el-alert v-else-if="outputMapping && !outputMapping.confirmed" title="AI 已预填客户原表的回填列。请人工核对并确认；这里只决定结果写回哪些列，不参与商品匹配判断。" type="warning" :closable="false" />
    <el-alert v-else-if="project?.status === 'IMPORTED'" :title="isType2 ? '客户需求和回填字段已确认。请点击“执行 AI 同品比价”。' : '客户需求和回填字段已确认。请点击“开始规格匹配”。'" type="info" :closable="false" />
    <el-alert v-else-if="isType2" title="系统先按 SKU 或品牌+型号召回，再由 AI 复核重要附加条件；完全同品取合规最低协议价，只有需求明确允许且无合规同品时才推荐带差异备注的替代品。" type="success" :closable="false" />
    <el-alert v-else-if="isType1" title="系统会保留全部满足规格参数且价格合规的商品；页面优先显示有匹配结果的需求行，导出仍按客户原表顺序，并在同一需求行右侧按回填字段组展开全部命中商品。" type="info" :closable="false" />
    <el-alert v-else title="该工作台仅用于类型 1、2。" type="warning" :closable="false" />

    <el-card v-if="inputMapping" class="mapping-card">
      <el-tabs v-model="mappingTab" class="mapping-tabs">
        <el-tab-pane label="1. 需求主要字段" name="input">
      <div v-loading="inputStructureLoading">
      <div class="mapping-title"><div><strong>客户需求主要字段确认</strong><p>AI 先预识别主要参考字段，人工确认后才解析需求并允许匹配</p></div><el-tag :type="inputMapping.confirmed ? 'success' : 'warning'">{{ inputMapping.confirmed ? "已确认" : "待确认" }}</el-tag></div>
      <el-alert title="这里只确认需要提升为结构化主参考的字段。未映射的其他非空客户列仍会完整保留，并作为 AI 的次要上下文参考；类型 1、2 的主条件和代码硬规则不会因此改变。结果回填列在第二个页签单独确认。" type="info" :closable="false" show-icon />
      <div class="input-structure-controls">
        <label>工作表<el-select v-model="inputSheetName" filterable @change="refreshInputStructure"><el-option v-for="sheet in inputMapping.sheet_names" :key="sheet" :label="sheet" :value="sheet" /></el-select></label>
        <label>表头行<el-input-number v-model="inputHeaderRow" :min="1" @change="refreshInputStructure" /></label>
        <label>数据起始行<el-input-number v-model="inputDataStartRow" :min="inputHeaderRow + 1" /></label>
      </div>
      <div class="output-mapping-table">
        <div class="output-mapping-head"><span>客户 Excel 列（不可修改）</span><span>{{ isType2 ? "类型 2 需求字段" : "类型 1 需求字段" }}（可搜索选择）</span></div>
        <div v-for="(header, index) in inputMapping.headers" :key="header" class="output-mapping-row">
          <div class="output-field"><span class="field-index">{{ index + 1 }}</span><span>{{ header }}</span></div>
          <el-select v-model="inputMappingSelections[header]" clearable filterable placeholder="次要参考（不设为主字段）">
            <el-option v-for="field in inputMapping.fields" :key="field.key" :label="field.label" :value="field.key" />
          </el-select>
        </div>
      </div>
      <div class="mapping-actions"><el-button type="primary" :loading="inputMappingSaving" :disabled="!auth.hasPermission('bid:update') || project?.status !== 'IMPORTED'" @click="confirmInputMapping">{{ inputMapping.confirmed ? "重新解析" : "确认并解析" }}</el-button></div>
      </div>
        </el-tab-pane>
        <el-tab-pane label="2. 结果回填字段" name="output" :disabled="!outputMapping">
      <template v-if="outputMapping">
      <div class="mapping-title"><div><strong>客户原表回填字段</strong><p>{{ outputMapping.sheet_name }} · 第 {{ outputMapping.header_row }} 行表头</p></div><el-tag :type="outputMapping.confirmed ? 'success' : 'warning'">{{ outputMapping.confirmed ? "已确认" : "待确认" }}</el-tag></div>
      <el-alert title="AI 只负责预识别回填列；人工修改这里不会改变类型 1 的规格匹配，也不会改变类型 2 的品牌型号同品判断。" type="info" :closable="false" show-icon />
      <div class="output-mapping-table">
        <div class="output-mapping-head"><span>客户原表列（不可修改）</span><span>商品主数据／报价结果字段（可搜索选择）</span></div>
        <div v-for="(header, index) in outputMappingHeaders" :key="header" class="output-mapping-row">
          <div class="output-field"><span class="field-index">{{ index + 1 }}</span><span>{{ header }}</span></div>
          <div class="mapping-selector"><el-select v-model="outputMappingSelections[header]" clearable filterable placeholder="选择回填内容">
              <el-option v-for="field in outputMapping.fields" :key="field.key" :label="field.required ? `${field.label}（必填）` : field.label" :value="field.key" />
            </el-select><el-button link type="danger" @click="removeOutputHeader(header)">移除</el-button></div>
        </div>
        <el-empty v-if="outputMappingHeaders.length === 0" description="AI 未识别到待回填列，请从下方人工补充" :image-size="60" />
      </div>
      <div class="mapping-actions"><el-select v-model="additionalOutputHeader" filterable clearable placeholder="从本次上传模板补充待回填列"><el-option v-for="header in outputMapping.headers" :key="header" :label="header" :value="header" :disabled="outputMappingHeaders.includes(header)" /></el-select><el-button :disabled="!additionalOutputHeader" @click="addOutputHeader">添加列</el-button><el-button type="primary" :loading="mappingSaving" :disabled="!auth.hasPermission('bid:update')" @click="confirmOutputMapping">{{ outputMapping.confirmed ? "保存映射" : "确认映射" }}</el-button></div>
      </template>
        </el-tab-pane>
      </el-tabs>
    </el-card>

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
        <el-table-column label="匹配商品" min-width="190"><template #default="{ row }"><template v-if="row.current_selection"><div>{{ snapshot(row.current_selection, "product_snapshot").product_name }}</div><small>{{ snapshot(row.current_selection, "product_snapshot").brand }} {{ snapshot(row.current_selection, "product_snapshot").model }}</small><small v-if="isType1" class="match-hint">全部命中商品将横向回填导出</small></template><span v-else>—</span></template></el-table-column>
        <el-table-column label="供应商" min-width="170"><template #default="{ row }"><template v-if="row.current_selection">{{ snapshot(row.current_selection, "supplier_snapshot").supplier_name }}</template><span v-else>—</span></template></el-table-column>
        <el-table-column :label="isType2 ? '最低协议价' : '协议价'"><template #default="{ row }">{{ row.current_selection?.selected_unit_price ?? "—" }}</template></el-table-column>
        <el-table-column v-if="isType2" label="推荐类型" width="110"><template #default="{ row }"><el-tag v-if="row.current_selection" :type="snapshot(row.current_selection, 'product_snapshot').type2_match_type === 'TYPE2_AI_SUBSTITUTE' ? 'warning' : 'success'">{{ snapshot(row.current_selection, "product_snapshot").type2_match_type === "TYPE2_AI_SUBSTITUTE" ? "同类型替代" : "完全同品" }}</el-tag><span v-else>—</span></template></el-table-column>
        <el-table-column v-if="isType2" label="匹配备注" min-width="260"><template #default="{ row }">{{ row.current_selection?.note ?? "—" }}</template></el-table-column>
        <el-table-column v-if="isType1" label="处理" fixed="right" width="170"><template #default="{ row }"><el-button v-if="canSelect(row) && ['UNIQUE_MATCH', 'MULTIPLE_MATCH', 'SELECTED'].includes(row.status)" link type="primary" @click="openCandidates(row)">查看全部匹配</el-button><el-button v-if="canSelect(row)" link type="warning" @click="openNoQuote(row)">无法报价</el-button></template></el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @current-change="load" @size-change="page = 1; load()" />
    </el-card>

    <el-drawer v-model="drawer" title="匹配候选商品" size="min(920px, 95vw)">
      <el-table v-loading="candidateLoading" :data="candidates">
        <el-table-column prop="rank" label="排名" width="70" /><el-table-column prop="product_name" label="商品" min-width="180" /><el-table-column prop="brand" label="品牌" /><el-table-column prop="model" label="型号" />
        <el-table-column label="供应商" min-width="160"><template #default="{ row }">{{ row.supplier_name }}</template></el-table-column><el-table-column prop="agreement_price" label="协议价" />
        <el-table-column v-if="!isType1" label="操作" width="90"><template #default="{ row }"><el-button link type="primary" @click="pick(row)">选择</el-button></template></el-table-column>
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
.match-hint { display: block; margin-top: 4px; color: #2670ca; }
.mapping-title { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.mapping-title p { margin: 4px 0 0; color: #6b7280; }
.mapping-tabs :deep(.el-tabs__content) { padding-top: 8px; }
.input-structure-controls { display: flex; flex-wrap: wrap; gap: 18px; margin-top: 16px; }
.input-structure-controls label { display: flex; align-items: center; gap: 8px; color: #606266; }
.input-structure-controls .el-select { width: 240px; }
.output-mapping-table { margin-top: 16px; overflow: hidden; border: 1px solid #dfe4ec; border-radius: 8px; }
.output-mapping-head, .output-mapping-row { display: grid; grid-template-columns: minmax(280px, 1fr) minmax(420px, 1fr); align-items: center; }
.output-mapping-head { min-height: 42px; padding: 0 14px; background: #f5f7fa; color: #303133; font-weight: 600; }
.output-mapping-row { min-height: 48px; padding: 0 14px; border-top: 1px solid #ebeef5; }
.output-mapping-row .el-select { width: 100%; }
.mapping-selector { display: flex; align-items: center; gap: 10px; }
.output-field { display: flex; align-items: center; gap: 10px; min-width: 0; }
.field-index { display: inline-flex; flex: 0 0 24px; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; background: #ecf5ff; color: #409eff; font-size: 12px; }
.mapping-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.mapping-actions .el-select { width: min(420px, 45vw); }
.header-actions { display: flex; flex-wrap: wrap; gap: 10px; }
.filter-form { margin-bottom: 4px; }
.filter-form .el-input { width: 320px; }
.filter-form .el-select { width: 180px; }
.el-pagination { justify-content: flex-end; margin-top: 16px; }
.el-dialog .el-input, .el-dialog .el-select { width: 100%; margin-top: 12px; }
@media (max-width: 800px) { .workbench-header { align-items: flex-start; flex-direction: column; } .filter-form .el-input, .filter-form .el-select { width: 100%; } .output-mapping-head, .output-mapping-row { grid-template-columns: minmax(180px, 0.8fr) minmax(240px, 1.2fr); } .output-mapping-table { overflow-x: auto; } }
</style>
