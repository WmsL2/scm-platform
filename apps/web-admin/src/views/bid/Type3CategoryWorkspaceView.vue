<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue"
import { ElMessage } from "element-plus"
import { useRoute } from "vue-router"
import { bidApi } from "../../api/bid"
import {
  type3RecommendationApi,
  type Type3Node,
  type Type3Preview,
  type Type3Run,
  type Type3Sheet,
} from "../../api/type3Recommendation"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"

const route = useRoute()
const auth = useAuthStore()
const projectId = String(route.params.id)
const preview = ref<Type3Preview>()
const selected = ref<Record<string, string[]>>({})
const activeSheetName = ref("")
const keyword = ref("")
const selectionPage = ref(1)
const selectionPageSize = ref(30)
const manualLabel = ref("")
const manualLevel = ref<"LEVEL1" | "LEVEL2" | "LEVEL3">("LEVEL3")
const runs = ref<Type3Run[]>([])
const active = ref<Type3Run>()
const candidates = ref<Array<{
  id: string
  sheet_name: string
  product_snapshot: Record<string, unknown>
  price_snapshot: Record<string, unknown>
  confirmed_at: string | null
}>>([])
const busy = ref(false)

const activeSheet = computed(() => preview.value?.sheets.find((sheet) => sheet.sheet_name === activeSheetName.value))
const filteredNodes = computed(() => {
  const term = keyword.value.trim().toLocaleLowerCase()
  const nodes = activeSheet.value?.nodes ?? []
  return term
    ? nodes.filter((node) => `${node.code ?? ""} ${node.label}`.toLocaleLowerCase().includes(term))
    : nodes
})
const visibleNodes = computed(() => filteredNodes.value.slice(
  (selectionPage.value - 1) * selectionPageSize.value,
  selectionPage.value * selectionPageSize.value,
))
const currentSheetSelected = computed(() => selected.value[activeSheetName.value] ?? [])
const allVisibleSelected = computed(() => visibleNodes.value.length > 0 && visibleNodes.value.every((node) => currentSheetSelected.value.includes(node.node_id)))
const manualNodes = computed(() => (activeSheet.value?.nodes ?? []).filter(isManualNode))
const canStart = computed(() => Object.values(selected.value).some((nodes) => nodes.length > 0))

watch([activeSheetName, keyword, selectionPageSize], () => { selectionPage.value = 1 })

function message(error: unknown, fallback: string): string { return error instanceof HttpError ? error.response.message : fallback }
function isManualNode(node: Type3Node): boolean { return node.node_id.startsWith("manual:") }
function countSelected(sheetName: string): number { return selected.value[sheetName]?.length ?? 0 }
function changeSheet(sheetName: string): void { activeSheetName.value = sheetName; keyword.value = "" }
function selectedSheets(): Type3Sheet[] {
  return (preview.value?.sheets ?? []).filter((sheet) => countSelected(sheet.sheet_name) > 0).map((sheet) => ({
    ...sheet,
    nodes: sheet.nodes.filter((node) => selected.value[sheet.sheet_name]?.includes(node.node_id)),
  }))
}
function restoreSavedSelections(savedSheets: Type3Sheet[]): void {
  selected.value = {}
  const savedByName = new Map(savedSheets.map((sheet) => [sheet.sheet_name, sheet]))
  for (const workbookSheet of preview.value?.sheets ?? []) {
    const savedSheet = savedByName.get(workbookSheet.sheet_name)
    if (!savedSheet) { selected.value[workbookSheet.sheet_name] = []; continue }
    const availableNodeIds = new Set(workbookSheet.nodes.map((node) => node.node_id))
    for (const node of savedSheet.nodes) {
      if (isManualNode(node) && !availableNodeIds.has(node.node_id)) {
        workbookSheet.nodes.push(node)
        availableNodeIds.add(node.node_id)
      }
    }
    selected.value[workbookSheet.sheet_name] = savedSheet.nodes.map((node) => node.node_id).filter((nodeId) => availableNodeIds.has(nodeId))
  }
}
function updateSheetSelection(value: Array<string | number | boolean>): void {
  if (activeSheetName.value) selected.value[activeSheetName.value] = value.filter((item): item is string => typeof item === "string")
}
function toggleVisibleNodes(checked: boolean): void {
  const sheetName = activeSheetName.value
  if (!sheetName) return
  const current = new Set(selected.value[sheetName] ?? [])
  for (const node of visibleNodes.value) { if (checked) current.add(node.node_id); else current.delete(node.node_id) }
  selected.value[sheetName] = [...current]
}
function nodeLabel(node: Type3Node): string { return [node.code, node.label].filter(Boolean).join(" ") }
function addManualNode(): void {
  const sheet = activeSheet.value
  const label = manualLabel.value.trim()
  if (!sheet || !label) { ElMessage.error("请输入要补充的类目名称"); return }
  const existing = sheet.nodes.find((node) => node.label === label && node.level === manualLevel.value)
  const node = existing ?? { node_id: `manual:${Date.now()}-${sheet.nodes.length}`, coordinate: "手工", level: manualLevel.value, label, code: null }
  if (!existing) sheet.nodes.push(node)
  const current = new Set(selected.value[sheet.sheet_name] ?? [])
  current.add(node.node_id)
  selected.value[sheet.sheet_name] = [...current]
  manualLabel.value = ""
  ElMessage.success("已补充并勾选该类目")
}
function removeManualNode(node: Type3Node): void {
  const sheet = activeSheet.value
  if (!sheet || !isManualNode(node)) return
  const index = sheet.nodes.findIndex((item) => item.node_id === node.node_id)
  if (index < 0) return
  sheet.nodes.splice(index, 1)
  selected.value[sheet.sheet_name] = (selected.value[sheet.sheet_name] ?? []).filter((nodeId) => nodeId !== node.node_id)
  ElMessage.success("已移除手工补充类目")
}
async function load(): Promise<void> {
  const [workbookPreview, savedSheets] = await Promise.all([
    type3RecommendationApi.preview(projectId),
    type3RecommendationApi.savedSelections(projectId),
  ])
  preview.value = workbookPreview
  restoreSavedSelections(savedSheets)
  activeSheetName.value ||= workbookPreview.sheets[0]?.sheet_name ?? ""
  runs.value = await type3RecommendationApi.runs(projectId)
  active.value = runs.value[0]
  if (active.value) await loadCandidates()
}
async function save(): Promise<void> {
  busy.value = true
  try {
    await type3RecommendationApi.saveSelections(projectId, selectedSheets())
    ElMessage.success("已保存人工选择，刷新后会自动恢复")
  } catch (error) { ElMessage.error(message(error, "保存失败")) }
  finally { busy.value = false }
}
async function start(): Promise<void> {
  if (busy.value) return
  if (!canStart.value) { ElMessage.error("请先选择 Sheet，并勾选至少一个类目"); return }
  busy.value = true
  try {
    await type3RecommendationApi.saveSelections(projectId, selectedSheets())
    active.value = await type3RecommendationApi.start(projectId)
    runs.value = await type3RecommendationApi.runs(projectId)
    await loadCandidates()
    if (active.value.status === "FAILED") ElMessage.error(active.value.error ?? "类型 3 解析失败")
  } catch (error) { ElMessage({ message: message(error, "生成候选失败"), type: "error", grouping: true }) }
  finally { busy.value = false }
}
async function loadCandidates(): Promise<void> { if (active.value) candidates.value = (await type3RecommendationApi.candidates(active.value.id)).items }
async function confirm(id: string): Promise<void> {
  try { await type3RecommendationApi.confirm([id]); await loadCandidates() }
  catch (error) { ElMessage.error(message(error, "确认失败")) }
}
async function completeSelection(): Promise<void> {
  if (!active.value) return
  busy.value = true
  try { await type3RecommendationApi.completeSelection(projectId, active.value.id); await load(); ElMessage.success("已完成选品，可以按 Sheet 导出") }
  catch (error) { ElMessage.error(message(error, "完成选品失败")) }
  finally { busy.value = false }
}
async function exportFile(): Promise<void> {
  if (!active.value) return
  busy.value = true
  try {
    const file = await type3RecommendationApi.export(projectId, active.value.id)
    const blob = await type3RecommendationApi.download(active.value.id, file.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url; link.download = file.original_filename; link.click(); URL.revokeObjectURL(url)
    ElMessage.success("已按 Sheet 写回导出")
  } catch (error) { ElMessage.error(message(error, "导出失败")) }
  finally { busy.value = false }
}
onMounted(() => { void bidApi.get(projectId); void load().catch((error) => ElMessage.error(message(error, "加载类型 3 工作台失败"))) })
</script>

<template>
  <div class="workspace">
    <header><p>TYPE 3 · SHEET CATEGORY SELECTION</p><h1>指定类目推品</h1><span>先选择 Sheet，再勾选一级、二级或三级类目。备注独立由 AI 分析，不会扩展你勾选的类目。</span></header>
    <el-card class="selector-card">
      <template #header><div class="selector-title"><strong>1. 选择 Sheet 与类目</strong><span>已选 {{ selectedSheets().length }} 个 Sheet、{{ Object.values(selected).flat().length }} 个类目</span></div></template>
      <div class="selector-layout">
        <aside class="sheet-list"><div class="sheet-list-title">客户工作表</div><button v-for="sheet in preview?.sheets" :key="sheet.sheet_name" type="button" :class="{ active: sheet.sheet_name === activeSheetName }" @click="changeSheet(sheet.sheet_name)"><span>{{ sheet.sheet_name }}</span><el-tag size="small" :type="countSelected(sheet.sheet_name) ? 'success' : 'info'">{{ countSelected(sheet.sheet_name) }} 已选</el-tag></button></aside>
        <section class="node-panel">
          <template v-if="activeSheet">
            <div class="node-toolbar"><div><strong>{{ activeSheet.sheet_name }}</strong><span>自动识别范围：此 Sheet 前 120 行、前 40 列；可手工补充类目。</span></div><el-input v-model="keyword" clearable placeholder="搜索类目名称或编码，如：饮水、6.1.2" class="search-input" /></div>
            <div class="manual-add"><el-select v-model="manualLevel" class="manual-level"><el-option label="一级类目" value="LEVEL1" /><el-option label="二级类目" value="LEVEL2" /><el-option label="三级类目" value="LEVEL3" /></el-select><el-input v-model="manualLabel" clearable placeholder="补充未识别到的类目" @keyup.enter="addManualNode" /><el-button @click="addManualNode">添加并勾选</el-button><div v-if="manualNodes.length" class="manual-nodes"><span>本 Sheet 手工补充：</span><el-tag v-for="node in manualNodes" :key="node.node_id" closable @close="removeManualNode(node)">{{ node.level.replace('LEVEL', '级') }} {{ nodeLabel(node) }}</el-tag></div></div>
            <div class="node-actions"><el-checkbox :model-value="allVisibleSelected" :indeterminate="!allVisibleSelected && visibleNodes.some((node) => currentSheetSelected.includes(node.node_id))" @change="(value: boolean) => toggleVisibleNodes(value)">全选当前页</el-checkbox><span>当前搜索到 {{ filteredNodes.length }} 个，展示 {{ visibleNodes.length }} 个</span></div>
            <el-checkbox-group :model-value="currentSheetSelected" class="node-grid" @update:model-value="updateSheetSelection"><el-checkbox v-for="node in visibleNodes" :key="node.node_id" :value="node.node_id" class="node-option"><el-tag size="small" effect="plain">{{ node.level.replace('LEVEL', '级') }}</el-tag><span>{{ nodeLabel(node) }}</span><small>{{ node.coordinate }}</small></el-checkbox></el-checkbox-group>
            <el-empty v-if="!visibleNodes.length" description="当前 Sheet 没有符合搜索条件的类目" />
            <el-pagination v-if="filteredNodes.length > selectionPageSize" v-model:current-page="selectionPage" v-model:page-size="selectionPageSize" :page-sizes="[20, 30, 50, 100]" layout="total, sizes, prev, pager, next" :total="filteredNodes.length" />
          </template>
          <el-empty v-else description="此工作簿没有可选择的 Sheet" />
        </section>
      </div>
    </el-card>
    <div class="actions"><el-button :loading="busy" :disabled="!auth.hasPermission('recommendation:create')" @click="save">保存人工选择</el-button><el-button type="primary" :loading="busy" :disabled="!canStart || !auth.hasPermission('recommendation:run')" @click="start">2. 解析备注并生成候选</el-button><el-button v-if="active" :loading="busy" :disabled="!auth.hasPermission('recommendation:review')" @click="completeSelection">完成选品</el-button><el-button v-if="active" type="success" :loading="busy" :disabled="!auth.hasPermission('recommendation:export')" @click="exportFile">按 Sheet 导出已确认商品</el-button></div>
    <el-card v-if="active"><template #header><strong>当前独立 Run · {{ active.status }}</strong><span class="muted"> {{ active.error }}</span></template><el-table :data="candidates"><el-table-column prop="sheet_name" label="来源 Sheet" /><el-table-column label="商品"><template #default="{ row }">{{ row.product_snapshot.product_name }}</template></el-table-column><el-table-column label="SKU"><template #default="{ row }">{{ row.product_snapshot.sku }}</template></el-table-column><el-table-column label="三级类目"><template #default="{ row }">{{ row.product_snapshot.category_level3_name }}</template></el-table-column><el-table-column label="协议价"><template #default="{ row }">{{ row.price_snapshot.agreement_price }}</template></el-table-column><el-table-column label="操作"><template #default="{ row }"><el-tag v-if="row.confirmed_at" type="success">已确认</el-tag><el-button v-else link type="primary" @click="confirm(row.id)">确认</el-button></template></el-table-column></el-table></el-card>
  </div>
</template>

<style scoped>
.workspace{display:grid;gap:18px}.workspace>header{padding:24px 28px;border-radius:14px;background:linear-gradient(135deg,#edf5ff,#f2f8f5)}h1{margin:4px 0}header p{margin:0;color:#2670ca;font-weight:700}.selector-title,.node-toolbar,.node-actions,.actions,.manual-add,.manual-nodes{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.selector-title{justify-content:space-between}.selector-title span,.node-toolbar span,.node-actions span,.muted{color:#909399;font-size:13px}.selector-layout{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:470px;border:1px solid #ebeef5;border-radius:10px;overflow:hidden}.sheet-list{background:#fafcff;border-right:1px solid #ebeef5;padding:12px;display:grid;align-content:start;gap:8px}.sheet-list-title{padding:4px 8px;color:#909399;font-size:13px}.sheet-list button{display:flex;align-items:center;justify-content:space-between;gap:8px;border:0;border-radius:7px;background:transparent;padding:11px 10px;text-align:left;color:#303133;cursor:pointer}.sheet-list button:hover,.sheet-list button.active{background:#ecf5ff;color:#1677d2}.node-panel{padding:20px;min-width:0}.node-toolbar{justify-content:space-between}.node-toolbar>div{display:grid;gap:4px}.search-input{max-width:360px}.manual-add{margin-top:14px;padding:12px;background:#f8fbff;border:1px dashed #b3d8ff;border-radius:7px}.manual-add .el-input{max-width:320px}.manual-level{width:120px}.manual-nodes{width:100%;padding-top:4px;color:#606266;font-size:13px}.node-actions{justify-content:space-between;margin:16px 0 10px;padding:9px 12px;background:#fafafa;border-radius:6px}.node-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:8px;min-height:260px;align-content:start}.node-option{display:flex;margin:0!important;padding:9px 10px;border:1px solid #ebeef5;border-radius:7px;white-space:normal}.node-option:hover{border-color:#a0cfff;background:#f5faff}.node-option span{margin-left:6px}.node-option small{margin-left:auto;color:#a8abb2}.el-pagination{justify-content:flex-end;margin-top:18px}@media(max-width:760px){.selector-layout{grid-template-columns:1fr}.sheet-list{border-right:0;border-bottom:1px solid #ebeef5;grid-template-columns:repeat(2,minmax(0,1fr))}.sheet-list-title{grid-column:1/-1}.node-toolbar{align-items:stretch}.search-input{max-width:none;width:100%}.node-grid{grid-template-columns:1fr}}
</style>
