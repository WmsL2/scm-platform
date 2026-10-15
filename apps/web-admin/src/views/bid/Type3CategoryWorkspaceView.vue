<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useRoute } from "vue-router"
import {
  type3RecommendationApi,
  type Type3Candidate,
  type Type3CandidatePage,
  type Type3CandidateSheetSummary,
  type Type3ExportField,
  type Type3Node,
  type Type3OutputColumn,
  type Type3Preview,
  type Type3Run,
  type Type3RunSheetSummary,
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
const outputColumns = ref<Type3OutputColumn[]>([])
const exportFields = ref<Type3ExportField[]>([])
const mappingSelections = ref<Record<number, string>>({})
const outputStructureLoading = ref(false)
const runs = ref<Type3Run[]>([])
const active = ref<Type3Run>()
const candidatePage = ref<Type3CandidatePage>()
const candidateSheetSummaries = ref<Type3CandidateSheetSummary[]>([])
const resultSheetName = ref<string>()
const resultPage = ref(1)
const resultPageSize = ref(50)
const selectedCandidateIds = ref<Set<string>>(new Set())
const excludedCandidateIds = ref<Set<string>>(new Set())
const selectAllUnconfirmed = ref(false)
const selectedConfirmedCandidateIds = ref<Set<string>>(new Set())
const excludedConfirmedCandidateIds = ref<Set<string>>(new Set())
const selectAllConfirmed = ref(false)
const detailCandidate = ref<Type3Candidate>()
const detailVisible = ref(false)
const busy = ref(false)
const savedSelectionSignature = ref("")

const activeSheet = computed(() => preview.value?.sheets.find((sheet) => sheet.sheet_name === activeSheetName.value))
const filteredNodes = computed(() => {
  const term = keyword.value.trim().toLocaleLowerCase()
  const nodes = activeSheet.value?.nodes ?? []
  return term ? nodes.filter((node) => `${node.code ?? ""} ${node.label}`.toLocaleLowerCase().includes(term)) : nodes
})
const visibleNodes = computed(() => filteredNodes.value.slice((selectionPage.value - 1) * selectionPageSize.value, selectionPage.value * selectionPageSize.value))
const currentSheetSelected = computed(() => selected.value[activeSheetName.value] ?? [])
const allVisibleSelected = computed(() => visibleNodes.value.length > 0 && visibleNodes.value.every((node) => currentSheetSelected.value.includes(node.node_id)))
const manualNodes = computed(() => (activeSheet.value?.nodes ?? []).filter(isManualNode))
const selectedSheetsMissingMapping = computed(() => selectedSheets().filter((sheet) => mappedColumnCount(sheet) === 0))
const canStart = computed(() => Object.values(selected.value).some((nodes) => nodes.length > 0) && selectedSheetsMissingMapping.value.length === 0)
const currentSelectionSignature = computed(() => sheetSignature(selectedSheets()))
const selectionDirty = computed(() => currentSelectionSignature.value !== savedSelectionSignature.value)
const currentSelectionSummary = computed(() => selectionSummary(selectedSheets()))
const runSelectionSummary = computed(() => active.value?.sheet_summaries ?? [])
const runIsOutdated = computed(() => Boolean(active.value) && (selectionDirty.value || scopeSignature(currentSelectionSummary.value) !== scopeSignature(runSelectionSummary.value)))
const candidateRows = computed(() => candidatePage.value?.items ?? [])
const candidateTotal = computed(() => candidatePage.value?.total ?? 0)
const unconfirmedTotal = computed(() => Math.max(0, candidateTotal.value - (candidatePage.value?.confirmed_total ?? 0)))
const confirmedTotal = computed(() => candidatePage.value?.confirmed_total ?? 0)
const selectedCandidateCount = computed(() => selectAllUnconfirmed.value ? Math.max(0, unconfirmedTotal.value - excludedCandidateIds.value.size) : selectedCandidateIds.value.size)
const selectedConfirmedCandidateCount = computed(() => selectAllConfirmed.value ? Math.max(0, confirmedTotal.value - excludedConfirmedCandidateIds.value.size) : selectedConfirmedCandidateIds.value.size)
const selectableCandidates = computed(() => candidateRows.value.filter((candidate) => !candidate.confirmed_at))
const confirmedCandidates = computed(() => candidateRows.value.filter((candidate) => candidate.confirmed_at))
const pageAllSelected = computed(() => selectableCandidates.value.length > 0 && selectableCandidates.value.every(isCandidateSelected))
const pagePartiallySelected = computed(() => selectableCandidates.value.some(isCandidateSelected) && !pageAllSelected.value)
const selectionEditable = computed(() => projectStatus.value === "SELECTING" && auth.hasPermission("recommendation:review"))
const selectionRecoveryAvailable = computed(() => Boolean(active.value) && projectStatus.value === "MATCHING" && active.value?.status === "WAITING_CONFIRMATION" && auth.hasPermission("recommendation:review"))
const resultSheetLabel = computed(() => resultSheetName.value ?? "全部来源 Sheet")
const projectStatus = computed(() => active.value?.project_status ?? "")

watch([activeSheetName, keyword, selectionPageSize], () => { selectionPage.value = 1 })

function message(error: unknown, fallback: string): string { return error instanceof HttpError ? error.response.message : fallback }
function isManualNode(node: Type3Node): boolean { return node.node_id.startsWith("manual:") }
function countSelected(sheetName: string): number { return selected.value[sheetName]?.length ?? 0 }
function selectionSummary(sheets: Type3Sheet[]): Type3RunSheetSummary[] { return sheets.map((sheet) => ({ sheet_name: sheet.sheet_name, selected_node_count: sheet.nodes.length })).sort((left, right) => left.sheet_name.localeCompare(right.sheet_name)) }
function scopeSignature(sheets: Type3RunSheetSummary[]): string { return sheets.map((sheet) => `${sheet.sheet_name}:${sheet.selected_node_count}`).sort().join("|") }
function sheetSignature(sheets: Type3Sheet[]): string {
  return sheets.map((sheet) => ({
    sheet_name: sheet.sheet_name,
    header_row: sheet.header_row,
    data_start_row: sheet.data_start_row,
    nodes: sheet.nodes.map((node) => node.node_id).sort(),
    columns: mappingColumnsOf(sheet).map((column) => `${column.column_index}:${column.field_key}`).sort(),
  })).sort((left, right) => left.sheet_name.localeCompare(right.sheet_name)).map((sheet) => JSON.stringify(sheet)).join("|")
}
function changeSheet(sheetName: string): void { persistOutputMapping(); activeSheetName.value = sheetName; keyword.value = ""; void loadOutputStructure() }
function selectedSheets(): Type3Sheet[] { return (preview.value?.sheets ?? []).filter((sheet) => countSelected(sheet.sheet_name) > 0).map((sheet) => ({ ...sheet, nodes: sheet.nodes.filter((node) => selected.value[sheet.sheet_name]?.includes(node.node_id)) })) }
function mappingColumnsOf(sheet: Type3Sheet): Array<{ column_index: number; field_key: string }> {
  const columns = sheet.mapping_json.columns
  return Array.isArray(columns) ? columns.filter((item): item is { column_index: number; field_key: string } => Boolean(item) && typeof item === "object" && typeof (item as Record<string, unknown>).column_index === "number" && typeof (item as Record<string, unknown>).field_key === "string") : []
}
function mappedColumnCount(sheet: Type3Sheet): number { return mappingColumnsOf(sheet).length }
function rebuildMappingSelections(sheet: Type3Sheet): void { mappingSelections.value = Object.fromEntries(mappingColumnsOf(sheet).map((item) => [item.column_index, item.field_key])) }
function persistOutputMapping(): void {
  const sheet = activeSheet.value
  if (!sheet) return
  sheet.mapping_json = { version: 2, columns: outputColumns.value.flatMap((column) => {
    const field = mappingSelections.value[column.column_index]
    return field ? [{ column_index: column.column_index, field_key: field }] : []
  }) }
}
async function loadOutputStructure(): Promise<void> {
  const sheet = activeSheet.value
  if (!sheet) { outputColumns.value = []; return }
  const sheetName = sheet.sheet_name
  outputStructureLoading.value = true
  try {
    const structure = await type3RecommendationApi.sheetOutputStructure(projectId, { sheetName, headerRow: sheet.header_row })
    if (activeSheetName.value !== sheetName) return
    outputColumns.value = structure.columns
    rebuildMappingSelections(sheet)
  } catch (error) {
    if (activeSheetName.value === sheetName) { outputColumns.value = []; mappingSelections.value = {}; ElMessage.error(message(error, "读取 Sheet 导出列失败")) }
  } finally { if (activeSheetName.value === sheetName) outputStructureLoading.value = false }
}
async function changeHeaderRow(value: number | undefined): Promise<void> {
  const sheet = activeSheet.value
  if (!sheet || !value) return
  sheet.header_row = value
  sheet.data_start_row = Math.max(sheet.data_start_row, value + 1)
  sheet.mapping_json = { version: 2, columns: [] }
  mappingSelections.value = {}
  await loadOutputStructure()
}
function restoreSavedSelections(savedSheets: Type3Sheet[]): void {
  selected.value = {}
  const savedByName = new Map(savedSheets.map((sheet) => [sheet.sheet_name, sheet]))
  for (const workbookSheet of preview.value?.sheets ?? []) {
    const savedSheet = savedByName.get(workbookSheet.sheet_name)
    if (!savedSheet) { selected.value[workbookSheet.sheet_name] = []; continue }
    workbookSheet.header_row = savedSheet.header_row
    workbookSheet.data_start_row = savedSheet.data_start_row
    workbookSheet.mapping_json = savedSheet.mapping_json
    const availableNodeIds = new Set(workbookSheet.nodes.map((node) => node.node_id))
    for (const node of savedSheet.nodes) if (isManualNode(node) && !availableNodeIds.has(node.node_id)) { workbookSheet.nodes.push(node); availableNodeIds.add(node.node_id) }
    selected.value[workbookSheet.sheet_name] = savedSheet.nodes.map((node) => node.node_id).filter((nodeId) => availableNodeIds.has(nodeId))
  }
}
function updateSheetSelection(value: Array<string | number | boolean>): void { if (activeSheetName.value) selected.value[activeSheetName.value] = value.filter((item): item is string => typeof item === "string") }
function toggleVisibleNodes(checked: boolean): void { const sheetName = activeSheetName.value; if (!sheetName) return; const current = new Set(selected.value[sheetName] ?? []); for (const node of visibleNodes.value) { if (checked) current.add(node.node_id); else current.delete(node.node_id) }; selected.value[sheetName] = [...current] }
function nodeLabel(node: Type3Node): string { return [node.code, node.label].filter(Boolean).join(" ") }
function addManualNode(): void {
  const sheet = activeSheet.value; const label = manualLabel.value.trim()
  if (!sheet || !label) { ElMessage.error("请输入要补充的类目名称"); return }
  const existing = sheet.nodes.find((node) => node.label === label && node.level === manualLevel.value)
  const node = existing ?? { node_id: `manual:${Date.now()}-${sheet.nodes.length}`, coordinate: "手工", level: manualLevel.value, label, code: null }
  if (!existing) sheet.nodes.push(node)
  const current = new Set(selected.value[sheet.sheet_name] ?? []); current.add(node.node_id); selected.value[sheet.sheet_name] = [...current]
  manualLabel.value = ""; ElMessage.success("已补充并勾选该类目")
}
function removeManualNode(node: Type3Node): void { const sheet = activeSheet.value; if (!sheet || !isManualNode(node)) return; const index = sheet.nodes.findIndex((item) => item.node_id === node.node_id); if (index < 0) return; sheet.nodes.splice(index, 1); selected.value[sheet.sheet_name] = (selected.value[sheet.sheet_name] ?? []).filter((nodeId) => nodeId !== node.node_id); ElMessage.success("已移除手工补充类目") }
function resetCandidateSelection(): void {
  selectedCandidateIds.value = new Set()
  excludedCandidateIds.value = new Set()
  selectAllUnconfirmed.value = false
  selectedConfirmedCandidateIds.value = new Set()
  excludedConfirmedCandidateIds.value = new Set()
  selectAllConfirmed.value = false
}
function isCandidateSelected(candidate: Type3Candidate): boolean { return !candidate.confirmed_at && (selectAllUnconfirmed.value ? !excludedCandidateIds.value.has(candidate.id) : selectedCandidateIds.value.has(candidate.id)) }
function setCandidateSelected(candidate: Type3Candidate, checked: boolean): void { if (candidate.confirmed_at) return; if (selectAllUnconfirmed.value) { const next = new Set(excludedCandidateIds.value); if (checked) next.delete(candidate.id); else next.add(candidate.id); excludedCandidateIds.value = next; return }; const next = new Set(selectedCandidateIds.value); if (checked) next.add(candidate.id); else next.delete(candidate.id); selectedCandidateIds.value = next }
function setCurrentPageSelected(checked: boolean): void { for (const candidate of selectableCandidates.value) setCandidateSelected(candidate, checked) }
async function selectAllPendingCandidates(): Promise<void> {
  await refreshResults()
  if (!selectionEditable.value) return
  selectAllUnconfirmed.value = true
  selectedCandidateIds.value = new Set()
  excludedCandidateIds.value = new Set()
}
function isConfirmedCandidateSelected(candidate: Type3Candidate): boolean { return Boolean(candidate.confirmed_at) && (selectAllConfirmed.value ? !excludedConfirmedCandidateIds.value.has(candidate.id) : selectedConfirmedCandidateIds.value.has(candidate.id)) }
function setConfirmedCandidateSelected(candidate: Type3Candidate, checked: boolean): void { if (!candidate.confirmed_at) return; if (selectAllConfirmed.value) { const next = new Set(excludedConfirmedCandidateIds.value); if (checked) next.delete(candidate.id); else next.add(candidate.id); excludedConfirmedCandidateIds.value = next; return }; const next = new Set(selectedConfirmedCandidateIds.value); if (checked) next.add(candidate.id); else next.delete(candidate.id); selectedConfirmedCandidateIds.value = next }
function setCurrentPageConfirmedSelected(checked: boolean): void { for (const candidate of confirmedCandidates.value) setConfirmedCandidateSelected(candidate, checked) }
async function selectAllConfirmedCandidates(): Promise<void> {
  // Confirm/unconfirm changes both the candidate totals and the project state.  Reload
  // before calculating an all-scope selection so the next click never depends on a
  // browser refresh to see just-confirmed rows.
  await refreshResults()
  if (!selectionEditable.value || confirmedTotal.value === 0) return
  selectAllConfirmed.value = true
  selectedConfirmedCandidateIds.value = new Set()
  excludedConfirmedCandidateIds.value = new Set()
}
function productValue(candidate: Type3Candidate, key: string): string { const value = candidate.product_snapshot[key] ?? candidate.price_snapshot[key]; return value === null || value === undefined || value === "" ? "-" : String(value) }
function moneyValue(value: unknown): string { if (value === null || value === undefined || value === "") return "-"; const numeric = Number(value); return Number.isFinite(numeric) ? `¥ ${numeric.toFixed(2)}` : String(value) }
function ratioValue(value: unknown): string { if (value === null || value === undefined || value === "") return "-"; const numeric = Number(value); return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value) }
function candidateImageUrl(candidate: Type3Candidate): string | undefined { const reference = candidate.product_snapshot.image_reference; if (typeof reference !== "string" || !reference) return undefined; if (/^https?:\/\//i.test(reference)) return reference; return `${(import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "")}/${reference.replace(/^\//, "")}` }
function openDetail(candidate: Type3Candidate): void { detailCandidate.value = candidate; detailVisible.value = true }
async function loadCandidateSheets(): Promise<void> { if (!active.value) { candidateSheetSummaries.value = []; return }; candidateSheetSummaries.value = await type3RecommendationApi.candidateSheets(active.value.id) }
async function loadCandidates(): Promise<void> { if (!active.value) { candidatePage.value = undefined; return }; candidatePage.value = await type3RecommendationApi.candidates(active.value.id, { page: resultPage.value, pageSize: resultPageSize.value, sheetName: resultSheetName.value }) }
async function refreshResults(): Promise<void> {
  const runId = active.value?.id
  if (!runId) { candidatePage.value = undefined; candidateSheetSummaries.value = []; return }
  const [latestRun, page, sheetSummaries] = await Promise.all([
    type3RecommendationApi.run(runId),
    type3RecommendationApi.candidates(runId, { page: resultPage.value, pageSize: resultPageSize.value, sheetName: resultSheetName.value }),
    type3RecommendationApi.candidateSheets(runId),
  ])
  if (active.value?.id !== runId) return
  active.value = latestRun
  runs.value = runs.value.map((item) => item.id === runId ? latestRun : item)
  candidatePage.value = page
  candidateSheetSummaries.value = sheetSummaries
}
async function changeResultSheet(sheetName?: string): Promise<void> { resultSheetName.value = sheetName; resultPage.value = 1; resetCandidateSelection(); await loadCandidates() }
async function changeResultPage(page: number): Promise<void> { resultPage.value = page; await loadCandidates() }
async function changeResultPageSize(pageSize: number): Promise<void> { resultPageSize.value = pageSize; resultPage.value = 1; await loadCandidates() }
async function load(): Promise<void> {
  const [workbookPreview, savedSheets, fields] = await Promise.all([type3RecommendationApi.preview(projectId), type3RecommendationApi.savedSelections(projectId), type3RecommendationApi.exportFields(projectId)])
  preview.value = workbookPreview; restoreSavedSelections(savedSheets); savedSelectionSignature.value = sheetSignature(savedSheets); activeSheetName.value ||= workbookPreview.sheets[0]?.sheet_name ?? ""
  exportFields.value = fields; await loadOutputStructure(); runs.value = await type3RecommendationApi.runs(projectId); active.value = runs.value[0]; resultSheetName.value = undefined; resultPage.value = 1; resetCandidateSelection(); await refreshResults()
}
async function persistAndVerifySelection(): Promise<Type3Sheet[]> {
  persistOutputMapping()
  const expected = selectedSheets()
  await type3RecommendationApi.saveSelections(projectId, expected)
  const savedSheets = await type3RecommendationApi.savedSelections(projectId)
  if (sheetSignature(savedSheets) !== sheetSignature(expected)) throw new Error("保存校验失败：服务端保存的 Sheet/类目与当前选择不一致")
  restoreSavedSelections(savedSheets)
  savedSelectionSignature.value = sheetSignature(savedSheets)
  await loadOutputStructure()
  return savedSheets
}
async function save(): Promise<void> { busy.value = true; try { const savedSheets = await persistAndVerifySelection(); ElMessage.success(`已确认保存 ${savedSheets.length} 个 Sheet、${savedSheets.reduce((total, sheet) => total + sheet.nodes.length, 0)} 个类目`) } catch (error) { ElMessage.error(error instanceof Error && error.message.startsWith("保存校验失败") ? error.message : message(error, "保存失败")) } finally { busy.value = false } }
async function start(): Promise<void> {
  if (busy.value) return
  persistOutputMapping()
  if (!Object.values(selected.value).some((nodes) => nodes.length > 0)) { ElMessage.error("请先选择 Sheet，并勾选至少一个类目"); return }
  if (selectedSheetsMissingMapping.value.length) { ElMessage.error(`请先配置导出字段映射：${selectedSheetsMissingMapping.value.map((sheet) => sheet.sheet_name).join("、")}`); return }
  busy.value = true
  try { const startedRun = await type3RecommendationApi.start(projectId, selectedSheets()); savedSelectionSignature.value = currentSelectionSignature.value; runs.value = await type3RecommendationApi.runs(projectId); active.value = runs.value.find((run) => run.id === startedRun.id) ?? startedRun; resultSheetName.value = undefined; resultPage.value = 1; resetCandidateSelection(); await refreshResults(); if (active.value.status === "FAILED") ElMessage.error(active.value.error ?? "类型 3 解析失败") } catch (error) { ElMessage({ message: message(error, "生成候选失败"), type: "error", grouping: true }) } finally { busy.value = false }
}
async function confirmCandidates(): Promise<void> {
  if (!active.value || selectedCandidateCount.value === 0) { ElMessage.warning("请先勾选需要确认的候选商品"); return }
  busy.value = true
  try { const confirmedCount = await type3RecommendationApi.confirmCandidates(active.value.id, selectAllUnconfirmed.value ? { select_all_unconfirmed: true, excluded_candidate_ids: [...excludedCandidateIds.value], sheet_name: resultSheetName.value } : { candidate_ids: [...selectedCandidateIds.value] }); resetCandidateSelection(); await refreshResults(); ElMessage.success(`已确认 ${confirmedCount} 件商品`) } catch (error) { ElMessage.error(message(error, "批量确认失败")) } finally { busy.value = false }
}
async function confirmOne(candidate: Type3Candidate): Promise<void> { if (!active.value) return; busy.value = true; try { await type3RecommendationApi.confirmCandidates(active.value.id, { candidate_ids: [candidate.id] }); await refreshResults(); ElMessage.success("已确认商品") } catch (error) { ElMessage.error(message(error, "确认失败")) } finally { busy.value = false } }
async function unconfirmCandidates(): Promise<void> {
  if (!active.value || selectedConfirmedCandidateCount.value === 0) { ElMessage.warning("请先选择需要撤销确认的商品"); return }
  try {
    await ElMessageBox.confirm(
      `确认撤销 ${selectedConfirmedCandidateCount.value} 件商品的确认状态？历史导出文件不会受影响。`,
      "撤销确认",
      { type: "warning", confirmButtonText: "确认撤销", cancelButtonText: "取消" },
    )
  } catch { return }
  busy.value = true
  try {
    const count = await type3RecommendationApi.unconfirmCandidates(active.value.id, selectAllConfirmed.value ? { select_all_confirmed: true, excluded_candidate_ids: [...excludedConfirmedCandidateIds.value], sheet_name: resultSheetName.value } : { candidate_ids: [...selectedConfirmedCandidateIds.value] })
    resetCandidateSelection()
    await refreshResults()
    ElMessage.success(`已撤销 ${count} 件商品的确认`)
  } catch (error) { ElMessage.error(message(error, "撤销确认失败")) } finally { busy.value = false }
}
async function unconfirmOne(candidate: Type3Candidate): Promise<void> {
  selectedConfirmedCandidateIds.value = new Set([candidate.id])
  selectAllConfirmed.value = false
  await unconfirmCandidates()
}
async function completeSelection(): Promise<void> { if (!active.value) return; busy.value = true; try { await type3RecommendationApi.completeSelection(projectId, active.value.id); await load(); ElMessage.success("已完成选品，可以按 Sheet 导出") } catch (error) { ElMessage.error(message(error, "完成选品失败")) } finally { busy.value = false } }
async function reopenSelection(): Promise<void> { if (!active.value) return; busy.value = true; try { await type3RecommendationApi.reopenSelection(projectId, active.value.id); await load(); ElMessage.success("已返回待选品状态") } catch (error) { ElMessage.error(message(error, "返回调整选品失败")) } finally { busy.value = false } }
async function recoverSelection(): Promise<void> { if (!active.value) return; busy.value = true; try { await type3RecommendationApi.recoverSelection(projectId, active.value.id); await load(); ElMessage.success("已恢复待选品状态，无需重新调用 AI") } catch (error) { ElMessage.error(message(error, "恢复待选品失败")) } finally { busy.value = false } }
async function exportFile(): Promise<void> { if (!active.value) return; busy.value = true; try { const file = await type3RecommendationApi.export(projectId, active.value.id); const blob = await type3RecommendationApi.download(active.value.id, file.id); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = file.original_filename; link.click(); URL.revokeObjectURL(url); ElMessage.success("已按 Sheet 写回导出") } catch (error) { ElMessage.error(message(error, "导出失败")) } finally { busy.value = false } }
onMounted(() => { void load().catch((error) => ElMessage.error(message(error, "加载类型 3 工作台失败"))) })
</script>

<template>
  <div class="workspace">
    <header><p>TYPE 3 · SHEET CATEGORY SELECTION</p><h1>指定类目推品</h1><span>先选择 Sheet，再勾选一级、二级或三级类目。备注独立由 AI 分析；泛类目可映射多个用途相关的真实三级类目，但不会扩展为无关类目。</span></header>
    <el-card class="selector-card">
      <template #header><div class="selector-title"><strong>1. 选择 Sheet 与类目</strong><span>当前选择 {{ selectedSheets().length }} 个 Sheet、{{ Object.values(selected).flat().length }} 个类目 <el-tag :type="selectionDirty ? 'warning' : 'success'" size="small">{{ selectionDirty ? '未保存' : '已确认保存' }}</el-tag></span></div></template>
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
          </template><el-empty v-else description="此工作簿没有可选择的 Sheet" />
        </section>
      </div>
    </el-card>
    <el-card v-if="activeSheet && countSelected(activeSheet.sheet_name)" class="mapping-card">
      <template #header><div class="result-header"><div><strong>1.5 {{ activeSheet.sheet_name }} 导出字段映射</strong><span class="muted">左侧是此 Sheet 表头行的实际列；右侧选择导出时要写入的商品主数据字段。每个 Sheet 独立保存。</span></div><el-tag :type="mappedColumnCount(activeSheet) ? 'success' : 'warning'">{{ mappedColumnCount(activeSheet) ? `已映射 ${mappedColumnCount(activeSheet)} 列` : '待配置' }}</el-tag></div></template>
      <el-alert title="首次会按标准表头自动预选；表头不同、列顺序不同或有重复表头时，请在这里手动调整。修改后点击“保存人工选择”，再生成候选。" type="info" :closable="false" class="mapping-tip" />
      <div class="mapping-meta"><strong>工作表：{{ activeSheet.sheet_name }}</strong><el-input-number :model-value="activeSheet.header_row" :min="1" :max="Math.max(1, activeSheet.max_row)" controls-position="right" @change="changeHeaderRow" /><span>表头行</span><el-input-number v-model="activeSheet.data_start_row" :min="activeSheet.header_row + 1" :max="Math.max(activeSheet.header_row + 1, activeSheet.max_row + 1)" controls-position="right" @change="persistOutputMapping" /><span>数据起始行</span><el-button :loading="outputStructureLoading" @click="loadOutputStructure">重新读取本行表头</el-button></div>
      <div v-loading="outputStructureLoading" class="mapping-table"><div class="mapping-table-head"><span>上传 Sheet 列（不可修改）</span><span>商品主数据字段（可搜索选择）</span></div><div v-for="column in outputColumns" :key="column.column_index" class="mapping-row"><div class="template-column"><span class="column-index">{{ column.column_index }}</span><span>{{ column.header }}</span><el-tag v-if="column.duplicate" type="warning" size="small">重复表头，按第 {{ column.column_index }} 列映射</el-tag></div><el-select v-model="mappingSelections[column.column_index]" filterable clearable placeholder="搜索并选择商品主数据字段" @change="persistOutputMapping"><el-option v-for="field in exportFields" :key="field.key" :label="field.label" :value="field.key" /></el-select></div><el-empty v-if="!outputStructureLoading && !outputColumns.length" description="当前表头行没有可映射列，请调整表头行" :image-size="70" /></div>
    </el-card>
    <el-alert v-if="activeSheet && !countSelected(activeSheet.sheet_name)" title="此 Sheet 未选类目，不需要配置导出映射；只有已选 Sheet 才会进入候选和导出。" type="info" :closable="false" />
    <div class="actions"><el-button :loading="busy" :disabled="!auth.hasPermission('recommendation:create')" @click="save">保存全部 Sheet 选择</el-button><el-button type="primary" :loading="busy" :disabled="!canStart || !auth.hasPermission('recommendation:run')" @click="start">保存并重新生成候选</el-button><el-button v-if="selectionRecoveryAvailable" type="warning" :loading="busy" @click="recoverSelection">恢复待选品</el-button><el-button v-if="active && projectStatus === 'SELECTING'" :loading="busy" :disabled="!auth.hasPermission('recommendation:review')" @click="completeSelection">完成选品</el-button><el-button v-if="active && ['READY', 'EXPORTED'].includes(projectStatus)" :loading="busy" :disabled="!auth.hasPermission('recommendation:review')" @click="reopenSelection">返回调整选品</el-button><el-button v-if="active" type="success" :loading="busy" :disabled="!auth.hasPermission('recommendation:export')" @click="exportFile">按 Sheet 导出已确认商品</el-button></div>
    <el-alert v-if="selectionEditable && confirmedTotal > 0" title="当前处于待选品状态：可继续确认候选，或撤销已确认商品；历史导出文件仍会保留。" type="info" :closable="false" />
    <el-card v-if="active">
      <template #header><div class="result-header"><div><strong>候选商品与人工确认</strong><span class="muted">当前仅展示 {{ resultSheetLabel }} 的候选；候选按来源 Sheet 隔离，确认和导出也不会串到其他 Sheet。</span></div><el-tag :type="active.status === 'FAILED' ? 'danger' : 'info'">{{ active.status }}</el-tag></div></template>
      <el-alert v-if="active.error" :title="active.error" type="error" :closable="false" class="run-error" />
      <el-alert v-if="runIsOutdated" :title="`当前页面已保存/选择 ${scopeSignature(currentSelectionSummary)}；但下方是历史 Run，只按 ${scopeSignature(runSelectionSummary)} 生成。请点击“保存并重新生成候选”，旧结果不会自动混入新 Sheet。`" type="warning" :closable="false" class="run-error" />
      <div v-else class="run-scope"><span>本次 Run 实际范围：</span><el-tag v-for="sheet in runSelectionSummary" :key="sheet.sheet_name" type="success">{{ sheet.sheet_name }} · {{ sheet.selected_node_count }} 类目</el-tag></div>
      <div class="result-sheet-tabs"><el-button :type="resultSheetName ? 'default' : 'primary'" @click="changeResultSheet()">全部来源 Sheet（{{ candidateSheetSummaries.reduce((total, item) => total + item.total, 0) }}）</el-button><el-button v-for="sheet in candidateSheetSummaries" :key="sheet.sheet_name" :type="resultSheetName === sheet.sheet_name ? 'primary' : 'default'" @click="changeResultSheet(sheet.sheet_name)">{{ sheet.sheet_name }}（{{ sheet.total }}）</el-button></div>
      <div v-if="candidateTotal" class="candidate-toolbar"><div><el-checkbox :model-value="pageAllSelected" :indeterminate="pagePartiallySelected" :disabled="!selectionEditable || selectableCandidates.length === 0" @change="(value: string | number | boolean) => setCurrentPageSelected(Boolean(value))">全选本页待确认</el-checkbox><span class="muted"> {{ candidateTotal }} 件候选，{{ candidatePage?.confirmed_total ?? 0 }} 件已确认</span></div><div class="selection-actions"><el-button :disabled="!selectionEditable" @click="setCurrentPageSelected(true)">全选本页待确认</el-button><el-button :disabled="!selectionEditable" @click="selectAllPendingCandidates">全选{{ resultSheetName ? '当前 Sheet' : '全部 Sheet' }}待确认商品</el-button><el-button :disabled="!selectionEditable" @click="setCurrentPageConfirmedSelected(true)">全选本页已确认</el-button><el-button :disabled="!selectionEditable" @click="selectAllConfirmedCandidates">全选{{ resultSheetName ? '当前 Sheet' : '全部 Sheet' }}已确认商品</el-button><el-button :disabled="!selectionEditable" @click="resetCandidateSelection">清空选择</el-button><el-button v-if="auth.hasPermission('recommendation:review')" type="primary" :loading="busy" :disabled="!selectionEditable || selectedCandidateCount === 0" @click="confirmCandidates">批量确认选中（{{ selectedCandidateCount }}）</el-button><el-button v-if="auth.hasPermission('recommendation:review')" type="danger" plain :loading="busy" :disabled="!selectionEditable || selectedConfirmedCandidateCount === 0" @click="unconfirmCandidates">批量撤销确认（{{ selectedConfirmedCandidateCount }}）</el-button></div></div>
      <el-table v-if="candidateTotal" :data="candidateRows" row-key="id" max-height="640">
        <el-table-column width="52" fixed="left"><template #default="{ row }"><el-checkbox :model-value="row.confirmed_at ? isConfirmedCandidateSelected(row) : isCandidateSelected(row)" :disabled="!selectionEditable" @change="(value: string | number | boolean) => row.confirmed_at ? setConfirmedCandidateSelected(row, Boolean(value)) : setCandidateSelected(row, Boolean(value))" /></template></el-table-column><el-table-column prop="rank" label="序号" width="70" fixed="left" />
        <el-table-column label="商品图片" width="108" fixed="left"><template #default="{ row }"><el-image v-if="candidateImageUrl(row)" class="candidate-image" :src="candidateImageUrl(row)" fit="contain" :preview-src-list="[candidateImageUrl(row)!]" preview-teleported /><div v-else class="image-placeholder">暂无图片</div></template></el-table-column><el-table-column label="SKU" min-width="140" fixed="left"><template #default="{ row }">{{ productValue(row, 'sku') }}</template></el-table-column><el-table-column label="商品名称" min-width="240" show-overflow-tooltip fixed="left"><template #default="{ row }">{{ productValue(row, 'product_name') }}</template></el-table-column>
        <el-table-column label="来源 Sheet" min-width="140" show-overflow-tooltip><template #default="{ row }">{{ row.sheet_name }}</template></el-table-column><el-table-column label="京东价" min-width="115"><template #default="{ row }">{{ moneyValue(row.price_snapshot.jd_price ?? row.product_snapshot.jd_price) }}</template></el-table-column><el-table-column label="折扣率" min-width="105"><template #default="{ row }">{{ ratioValue(row.price_snapshot.discount_rate ?? row.product_snapshot.discount_rate) }}</template></el-table-column><el-table-column label="一级类目" min-width="130"><template #default="{ row }">{{ productValue(row, 'category_level1_name') }}</template></el-table-column><el-table-column label="二级类目" min-width="130"><template #default="{ row }">{{ productValue(row, 'category_level2_name') }}</template></el-table-column><el-table-column label="三级类目" min-width="130"><template #default="{ row }">{{ productValue(row, 'category_level3_name') }}</template></el-table-column>
        <el-table-column label="确认状态" width="110" fixed="right"><template #default="{ row }"><el-tag :type="row.confirmed_at ? 'success' : 'info'">{{ row.confirmed_at ? '已确认' : '待确认' }}</el-tag></template></el-table-column><el-table-column label="操作" width="180" fixed="right"><template #default="{ row }"><el-button link type="primary" @click="openDetail(row)">查看详情</el-button><el-button v-if="!row.confirmed_at && selectionEditable" link type="primary" :loading="busy" @click="confirmOne(row)">确认选品</el-button><el-button v-else-if="row.confirmed_at && selectionEditable" link type="danger" :loading="busy" @click="unconfirmOne(row)">撤销确认</el-button></template></el-table-column>
      </el-table>
      <el-empty v-else description="当前范围暂无候选商品" /><el-pagination v-if="candidateTotal" v-model:current-page="resultPage" v-model:page-size="resultPageSize" :page-sizes="[20, 50, 100, 200]" :total="candidateTotal" layout="total, sizes, prev, pager, next" @current-change="changeResultPage" @size-change="changeResultPageSize" />
    </el-card>
    <el-dialog v-model="detailVisible" title="候选商品详情（本次冻结快照）" width="min(760px, 94vw)">
      <template v-if="detailCandidate"><div class="snapshot-detail"><el-image v-if="candidateImageUrl(detailCandidate)" class="detail-image" :src="candidateImageUrl(detailCandidate)" fit="contain" :preview-src-list="[candidateImageUrl(detailCandidate)!]" preview-teleported /><div v-else class="detail-image image-placeholder">暂无图片</div><el-descriptions :column="2" border><el-descriptions-item label="SKU">{{ productValue(detailCandidate, 'sku') }}</el-descriptions-item><el-descriptions-item label="商品名称">{{ productValue(detailCandidate, 'product_name') }}</el-descriptions-item><el-descriptions-item label="品牌">{{ productValue(detailCandidate, 'brand') }}</el-descriptions-item><el-descriptions-item label="型号">{{ productValue(detailCandidate, 'model') }}</el-descriptions-item><el-descriptions-item label="一级 / 二级 / 三级类目" :span="2">{{ productValue(detailCandidate, 'category_level1_name') }} / {{ productValue(detailCandidate, 'category_level2_name') }} / {{ productValue(detailCandidate, 'category_level3_name') }}</el-descriptions-item><el-descriptions-item label="产品规格" :span="2">{{ productValue(detailCandidate, 'product_specification') }}</el-descriptions-item><el-descriptions-item label="卖点" :span="2">{{ productValue(detailCandidate, 'selling_points') }}</el-descriptions-item><el-descriptions-item label="京东价">{{ moneyValue(detailCandidate.price_snapshot.jd_price ?? detailCandidate.product_snapshot.jd_price) }}</el-descriptions-item><el-descriptions-item label="协议价">{{ moneyValue(detailCandidate.price_snapshot.agreement_price ?? detailCandidate.product_snapshot.agreement_price) }}</el-descriptions-item><el-descriptions-item label="折扣率">{{ ratioValue(detailCandidate.price_snapshot.discount_rate ?? detailCandidate.product_snapshot.discount_rate) }}</el-descriptions-item><el-descriptions-item label="毛利率">{{ ratioValue(detailCandidate.price_snapshot.gross_margin ?? detailCandidate.product_snapshot.gross_margin) }}</el-descriptions-item></el-descriptions></div><p class="snapshot-note">该窗口只读取本次候选生成时冻结的商品、价格与图片引用快照，不会因后续商品主数据修改而变化。</p></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.workspace{display:grid;gap:18px}.workspace>header{padding:24px 28px;border-radius:14px;background:linear-gradient(135deg,#edf5ff,#f2f8f5)}h1{margin:4px 0}header p{margin:0;color:#2670ca;font-weight:700}.selector-title,.node-toolbar,.node-actions,.actions,.manual-add,.manual-nodes,.result-header,.candidate-toolbar,.selection-actions,.result-sheet-tabs,.mapping-meta,.snapshot-detail{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.selector-title,.result-header,.candidate-toolbar{justify-content:space-between}.selector-title span,.node-toolbar span,.node-actions span,.muted,.snapshot-note{color:#909399;font-size:13px}.selector-layout{display:grid;grid-template-columns:250px minmax(0,1fr);min-height:470px;border:1px solid #ebeef5;border-radius:10px;overflow:hidden}.sheet-list{background:#fafcff;border-right:1px solid #ebeef5;padding:12px;display:grid;align-content:start;gap:8px}.sheet-list-title{padding:4px 8px;color:#909399;font-size:13px}.sheet-list button{display:flex;align-items:center;justify-content:space-between;gap:8px;border:0;border-radius:7px;background:transparent;padding:11px 10px;text-align:left;color:#303133;cursor:pointer}.sheet-list button:hover,.sheet-list button.active{background:#ecf5ff;color:#1677d2}.node-panel{padding:20px;min-width:0}.node-toolbar{justify-content:space-between}.node-toolbar>div{display:grid;gap:4px}.search-input{max-width:360px}.manual-add{margin-top:14px;padding:12px;background:#f8fbff;border:1px dashed #b3d8ff;border-radius:7px}.manual-add .el-input{max-width:320px}.manual-level{width:120px}.manual-nodes{width:100%;padding-top:4px;color:#606266;font-size:13px}.node-actions{justify-content:space-between;margin:16px 0 10px;padding:9px 12px;background:#fafafa;border-radius:6px}.node-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:8px;min-height:260px;align-content:start}.node-option{display:flex;margin:0!important;padding:9px 10px;border:1px solid #ebeef5;border-radius:7px;white-space:normal}.node-option:hover{border-color:#a0cfff;background:#f5faff}.node-option span{margin-left:6px}.node-option small{margin-left:auto;color:#a8abb2}.mapping-tip{margin-bottom:16px}.mapping-meta{margin-bottom:16px}.mapping-table{overflow:hidden;border:1px solid #e4e7ed;border-radius:8px;max-height:620px;overflow-y:auto}.mapping-table-head,.mapping-row{display:grid;grid-template-columns:minmax(240px,1fr) minmax(280px,1fr);gap:16px;align-items:center;padding:10px 14px}.mapping-table-head{position:sticky;top:0;background:#f5f7fa;color:#606266;font-weight:600;z-index:1}.mapping-row+.mapping-row{border-top:1px solid #ebeef5}.template-column{display:flex;align-items:center;gap:10px;min-width:0}.column-index{display:inline-grid;place-items:center;width:26px;height:26px;flex:0 0 auto;border-radius:50%;background:#ecf5ff;color:#409eff;font-size:12px}.result-sheet-tabs{padding:0 0 14px;border-bottom:1px solid #ebeef5}.candidate-toolbar{margin:16px 0}.run-error{margin-bottom:14px}.candidate-image,.detail-image{width:72px;height:72px}.detail-image{flex:0 0 auto}.image-placeholder{display:grid;place-items:center;width:72px;height:72px;color:#909399;background:#f5f7fa;border-radius:4px;font-size:12px}.snapshot-detail .el-descriptions{flex:1;min-width:min(560px,100%)}.snapshot-note{margin:12px 0 0}.el-pagination{justify-content:flex-end;margin-top:18px}@media(max-width:760px){.selector-layout{grid-template-columns:1fr}.sheet-list{border-right:0;border-bottom:1px solid #ebeef5;grid-template-columns:repeat(2,minmax(0,1fr))}.sheet-list-title{grid-column:1/-1}.node-toolbar{align-items:stretch}.search-input{max-width:none;width:100%}.node-grid{grid-template-columns:1fr}.candidate-toolbar,.result-header{align-items:flex-start}.mapping-table-head{display:none}.mapping-row{grid-template-columns:1fr;gap:8px}}
</style>
