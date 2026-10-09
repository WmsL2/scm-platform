<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { Setting } from "@element-plus/icons-vue"
import { useRoute, useRouter } from "vue-router"
import { bidApi } from "../../api/bid"
import { pptSolutionApi } from "../../api/pptSolution"
import { recommendationApi } from "../../api/recommendation"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type { BidProjectDetail } from "../../types/bid"
import type { PptGenerationTask, PptPackage, PptRecommendationMode } from "../../types/pptSolution"
import { type RecommendationCandidate, type RecommendationRun } from "../../types/recommendation"
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
const run = ref<RecommendationRun | null>(null)
const packages = ref<PptPackage[]>([])
const generations = ref<PptGenerationTask[]>([])
const selectedCandidateIds = ref<Set<string>>(new Set())
const excludedCandidateIds = ref<Set<string>>(new Set())
const selectAllCandidates = ref(false)
const candidatePage = ref(1)
const candidatePageSize = ref(50)
const candidateColumnStorageKey = "scm.ppt-direct-candidates.visible-columns.v1"
const selectedCandidateOptionalColumns = ref<RecommendationCandidateOptionalColumnKey[]>(restoreRecommendationCandidateOptionalColumns(localStorage.getItem(candidateColumnStorageKey)))
const packageVisible = ref(false)
const packageForm = reactive({ name: "", price_tier: "", reason: "", quantities: {} as Record<string, number> })
const recommendationConfig = reactive({ recommendation_mode: "SINGLE" as PptRecommendationMode, price_bands: [{ min_price: null as string | null, max_price: "50", item_count: 10 }], fulfillment_deadline: null as string | null })

const candidates = computed(() => run.value?.candidates ?? [])
const candidateTotal = computed(() => run.value?.candidate_page?.total ?? 0)
const unconfirmedTotal = computed(() => run.value?.candidate_page?.unconfirmed_total ?? 0)
const confirmed = computed(() => candidates.value.filter((item) => item.confirmation))
const selectionEditable = computed(() => project.value?.status === "SELECTING" && auth.hasPermission("recommendation:review"))
const canComplete = computed(() => selectionEditable.value && (run.value?.candidate_page?.confirmed_total ?? 0) > 0)
const canGenerate = computed(() => Boolean(run.value && ["READY", "EXPORTED"].includes(project.value?.status ?? "") && ["CONFIRMED", "EXPORTED"].includes(run.value.status)))
const selectedCandidateCount = computed(() => selectAllCandidates.value
  ? Math.max(0, unconfirmedTotal.value - excludedCandidateIds.value.size)
  : selectedCandidateIds.value.size)
const selectableOnPage = computed(() => candidates.value.filter((item) => !item.confirmation))
const pageAllSelected = computed(() => selectableOnPage.value.length > 0 && selectableOnPage.value.every(isCandidateSelected))
const pagePartiallySelected = computed(() => selectableOnPage.value.some(isCandidateSelected) && !pageAllSelected.value)
const visibleCandidateColumns = computed(() => selectedCandidateOptionalColumns.value.map((key) => RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS.find((column) => column.key === key)).filter((column): column is RecommendationCandidateOptionalColumn => Boolean(column)))

function messageFor(error: unknown, fallback: string): string { return error instanceof HttpError ? error.response.message : fallback }
function formatMoney(value: unknown): string { const numeric = Number(value); return Number.isFinite(numeric) ? `¥ ${numeric.toFixed(2)}` : "-" }
function productValue(candidate: RecommendationCandidate, key: string): string { const value = candidate.product_snapshot[key] ?? candidate.price_snapshot[key]; return value === null || value === undefined || value === "" ? "-" : String(value) }
function candidateImageUrl(candidate: RecommendationCandidate): string | undefined { const reference = candidate.product_snapshot.image_reference; if (typeof reference !== "string" || !reference) return undefined; if (/^https?:\/\//i.test(reference)) return reference; return `${(import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "")}/${reference.replace(/^\//, "")}` }
function candidateColumnValue(candidate: RecommendationCandidate, column: RecommendationCandidateOptionalColumn): string { const value = column.key === "supplier_name" ? candidate.supplier_snapshot.supplier_name : candidate.product_snapshot[column.key] ?? candidate.price_snapshot[column.key]; if (value === null || value === undefined || value === "") return "-"; if (column.format === "money") return formatMoney(value); if (column.format === "percent") { const ratio = Number(value); return Number.isFinite(ratio) ? `${(ratio * 100).toFixed(2)}%` : String(value) }; return String(value) }
function bandLabel(index: number): string { const band = recommendationConfig.price_bands[index]; return `${band.min_price ?? 0}–${band.max_price} 元 · AI 匹配 ${band.item_count} 件` }

async function load(): Promise<void> {
  loading.value = true
  try {
    project.value = await bidApi.get(projectId)
    if (project.value.project_type !== "PPT_SOLUTION") { ElMessage.warning("该项目不是类型 5 PPT 方案项目"); await router.replace(`/bid-projects/${projectId}`); return }
    const saved = await pptSolutionApi.config(projectId)
    if (saved) Object.assign(recommendationConfig, {
      recommendation_mode: saved.recommendation_mode === "MIXED" ? "COMBINATION" : saved.recommendation_mode,
      price_bands: saved.price_bands,
      fulfillment_deadline: saved.fulfillment_deadline,
    })
    const history = await recommendationApi.runs(projectId)
    const preferred = history.find((item) => ["WAITING_CONFIRMATION", "CONFIRMED", "EXPORTED", "ANALYZING", "RETRIEVING", "RANKING"].includes(item.status)) ?? history[0]
    run.value = preferred ? await recommendationApi.run(preferred.id, candidatePage.value, candidatePageSize.value) : null
    packages.value = run.value ? await pptSolutionApi.packages(run.value.id) : []
    generations.value = await pptSolutionApi.generations(projectId)
  } catch (error) { ElMessage.error(messageFor(error, "加载 PPT 选品失败")) }
  finally { loading.value = false }
}

async function refreshRun(): Promise<void> { if (run.value) { run.value = await recommendationApi.run(run.value.id, candidatePage.value, candidatePageSize.value); packages.value = await pptSolutionApi.packages(run.value.id) } }
async function startRun(): Promise<void> { acting.value = true; try { await pptSolutionApi.saveConfig(projectId, recommendationConfig); run.value = await recommendationApi.start(projectId); candidatePage.value = 1; resetCandidateSelection(); await load(); if (run.value?.status === "FAILED") ElMessage.error(run.value.error ?? "AI 商品匹配失败"); else ElMessage.success("AI 已按各价格档匹配商品，请勾选确认") } catch (error) { ElMessage.error(messageFor(error, "生成推品失败")) } finally { acting.value = false } }
function addPriceBand(): void { recommendationConfig.price_bands.push({ min_price: null, max_price: "", item_count: 10 }) }
function removePriceBand(index: number): void { if (recommendationConfig.price_bands.length > 1) recommendationConfig.price_bands.splice(index, 1) }
function resetCandidateSelection(): void { selectedCandidateIds.value = new Set(); excludedCandidateIds.value = new Set(); selectAllCandidates.value = false }
function isCandidateSelected(candidate: RecommendationCandidate): boolean { if (candidate.confirmation) return false; return selectAllCandidates.value ? !excludedCandidateIds.value.has(candidate.id) : selectedCandidateIds.value.has(candidate.id) }
function setCandidateSelected(candidate: RecommendationCandidate, checked: boolean): void { if (candidate.confirmation) return; if (selectAllCandidates.value) { const excluded = new Set(excludedCandidateIds.value); if (checked) excluded.delete(candidate.id); else excluded.add(candidate.id); excludedCandidateIds.value = excluded; return }; const values = new Set(selectedCandidateIds.value); if (checked) values.add(candidate.id); else values.delete(candidate.id); selectedCandidateIds.value = values }
function setCurrentPageSelected(checked: boolean): void { for (const candidate of selectableOnPage.value) setCandidateSelected(candidate, checked) }
function selectAllUnconfirmedCandidates(): void { selectAllCandidates.value = true; selectedCandidateIds.value = new Set(); excludedCandidateIds.value = new Set() }
async function changeCandidatePage(page: number): Promise<void> { candidatePage.value = page; await refreshRun() }
async function changeCandidatePageSize(size: number): Promise<void> { candidatePageSize.value = size; candidatePage.value = 1; await refreshRun() }
async function confirmSelectedCandidates(): Promise<void> { if (!run.value || !selectedCandidateCount.value) return; acting.value = true; try { const result = await recommendationApi.confirmMany(run.value.id, selectAllCandidates.value ? { selectAll: true, excludedCandidateIds: [...excludedCandidateIds.value] } : { candidateIds: [...selectedCandidateIds.value] }); resetCandidateSelection(); await refreshRun(); ElMessage.success(`已确认 ${result.confirmed_count} 件商品`) } catch (error) { ElMessage.error(messageFor(error, "批量确认选品失败")) } finally { acting.value = false } }
async function completeSelection(): Promise<void> { if (!run.value) return; try { await ElMessageBox.confirm(`确认完成选品？当前已确认 ${run.value.candidate_page?.confirmed_total ?? 0} 件商品。`, "完成选品", { type: "warning" }) } catch { return }; acting.value = true; try { await recommendationApi.completeSelection(projectId, run.value.id); await load(); ElMessage.success("选品已完成，可以生成 PPT") } catch (error) { ElMessage.error(messageFor(error, "完成选品失败")) } finally { acting.value = false } }
async function reopenSelection(): Promise<void> { if (!run.value) return; acting.value = true; try { await recommendationApi.reopenSelection(projectId, run.value.id); await load() } catch (error) { ElMessage.error(messageFor(error, "返回调整选品失败")) } finally { acting.value = false } }
function openPackage(): void { if (confirmed.value.length < 2) { ElMessage.warning("请先在本页确认至少两件商品"); return }; Object.assign(packageForm, { name: "", price_tier: "", reason: "", quantities: Object.fromEntries(confirmed.value.map((item) => [item.id, 0])) }); packageVisible.value = true }
async function createPackage(): Promise<void> { if (!run.value || !packageForm.name.trim()) { ElMessage.warning("请填写套装名称"); return }; const items = Object.entries(packageForm.quantities).filter(([, quantity]) => quantity > 0).map(([candidate_id, quantity]) => ({ candidate_id, quantity })); if (items.length < 2) { ElMessage.warning("一个套装至少包含两种商品"); return }; acting.value = true; try { await pptSolutionApi.createPackage(run.value.id, { name: packageForm.name.trim(), price_tier: packageForm.price_tier || null, reason: packageForm.reason || null, items }); packageVisible.value = false; await refreshRun() } catch (error) { ElMessage.error(messageFor(error, "保存套装失败")) } finally { acting.value = false } }
async function generatePpt(): Promise<void> { if (!run.value) return; acting.value = true; try { await pptSolutionApi.generate(projectId, run.value.id); generations.value = await pptSolutionApi.generations(projectId); ElMessage.success("正在生成 PPT") } catch (error) { ElMessage.error(messageFor(error, "PPT 生成失败")) } finally { acting.value = false } }
function isColumnSelected(key: RecommendationCandidateOptionalColumnKey): boolean { return selectedCandidateOptionalColumns.value.includes(key) }
function updateColumnSelection(key: RecommendationCandidateOptionalColumnKey, checked: unknown): void { selectedCandidateOptionalColumns.value = updateRecommendationCandidateOptionalColumns(selectedCandidateOptionalColumns.value, key, Boolean(checked)); localStorage.setItem(candidateColumnStorageKey, JSON.stringify(selectedCandidateOptionalColumns.value)) }
async function download(task: PptGenerationTask): Promise<void> { if (!task.output_file_id) return; const blob = await pptSolutionApi.download(task.id, task.output_file_id); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = `${project.value?.project_name ?? "PPT方案"}.pptx`; link.click(); URL.revokeObjectURL(link.href) }
onMounted(() => void load())
</script>

<template>
  <div v-loading="loading" class="workspace">
    <header><div><p>TYPE 5 · PPT SOLUTION</p><h1>{{ project?.project_name ?? "PPT 方案" }}</h1><span>{{ project?.remark }}</span></div><div class="actions"><el-button @click="router.push('/bid-projects')">返回项目</el-button><el-button v-if="!run || project?.status === 'SELECTING'" type="primary" :loading="acting" @click="startRun">{{ run ? '重新生成推品' : '生成推品' }}</el-button><el-button v-if="project?.status === 'SELECTING'" type="success" :disabled="!canComplete" :loading="acting" @click="completeSelection">完成选品</el-button><el-button v-else-if="['READY', 'EXPORTED'].includes(project?.status ?? '')" :loading="acting" @click="reopenSelection">返回调整选品</el-button></div></header>
    <el-alert v-if="run?.error" :title="run.error" type="warning" :closable="false" />
    <el-card v-if="!run || project?.status === 'SELECTING'"><template #header><div class="card-header"><strong>推品配置</strong><span class="muted">每个价格档单独填写 AI 需要匹配的商品数量。</span></div></template><el-form label-position="top" class="recommendation-config"><el-form-item label="推品方式"><el-radio-group v-model="recommendationConfig.recommendation_mode"><el-radio-button value="SINGLE">单品推品</el-radio-button><el-radio-button value="COMBINATION">组合推品</el-radio-button></el-radio-group></el-form-item><el-form-item label="价格档 / AI 匹配商品数量"><div class="price-bands"><div v-for="(band, index) in recommendationConfig.price_bands" :key="index" class="price-band"><el-input v-model="band.min_price" type="number" min="0" placeholder="最低价（可空）" /><span>至</span><el-input v-model="band.max_price" type="number" min="0.01" placeholder="最高价 *" /><el-input-number v-model="band.item_count" :min="1" :max="500" /><span>件商品</span><el-button link type="danger" :disabled="recommendationConfig.price_bands.length === 1" @click="removePriceBand(index)">删除</el-button></div><el-button @click="addPriceBand">新增价格档</el-button></div></el-form-item><el-form-item label="履约截止日"><el-date-picker v-model="recommendationConfig.fulfillment_deadline" type="date" value-format="YYYY-MM-DD" /></el-form-item><el-alert title="每个价格档按商品协议价筛选。AI 每档只匹配该档指定数量的商品，多个价格档不能重叠；匹配结果统一在下方表格中人工勾选确认。" type="info" :closable="false" /></el-form></el-card>
    <el-card v-if="run">
      <template #header>
        <div class="card-header">
          <div><strong>AI 匹配商品与人工确认</strong><span class="muted">AI 已按每档数量匹配商品；最终商品由人工勾选确认。</span></div>
          <div class="selection-actions">
            <el-button :disabled="!selectionEditable || unconfirmedTotal === 0" @click="selectAllUnconfirmedCandidates">全选所有待确认（{{ unconfirmedTotal }}）</el-button>
            <el-button :disabled="!selectionEditable" @click="resetCandidateSelection">清空选择</el-button>
            <el-popover placement="bottom-end" :width="340" trigger="click">
              <template #reference><el-button :icon="Setting">自定义显示列</el-button></template>
              <div class="column-picker"><el-checkbox v-for="option in RECOMMENDATION_CANDIDATE_OPTIONAL_COLUMNS" :key="option.key" :model-value="isColumnSelected(option.key)" @change="(checked: unknown) => updateColumnSelection(option.key, checked)">{{ option.label }}</el-checkbox></div>
            </el-popover>
            <el-button type="primary" :disabled="!selectionEditable || selectedCandidateCount === 0" :loading="acting" @click="confirmSelectedCandidates">批量确认选中（{{ selectedCandidateCount }}）</el-button>
          </div>
        </div>
      </template>
      <div class="band-tags"><el-tag v-for="(_, index) in recommendationConfig.price_bands" :key="index" type="success">{{ bandLabel(index) }}</el-tag><span class="muted">共匹配 {{ candidateTotal }} 件，已确认 {{ run.candidate_page?.confirmed_total ?? 0 }} 件</span></div>
      <el-table :data="candidates">
        <el-table-column width="52">
          <template #header><el-checkbox :model-value="pageAllSelected" :indeterminate="pagePartiallySelected" :disabled="!selectionEditable || selectableOnPage.length === 0" @change="(value: string | number | boolean) => setCurrentPageSelected(Boolean(value))" /></template>
          <template #default="{ row }"><el-checkbox :model-value="isCandidateSelected(row)" :disabled="!selectionEditable || Boolean(row.confirmation)" @change="(value: string | number | boolean) => setCandidateSelected(row, Boolean(value))" /></template>
        </el-table-column>
        <el-table-column prop="rank" label="序号" width="70" fixed="left" />
        <el-table-column label="商品图片" width="108" fixed="left"><template #default="{ row }"><el-image v-if="candidateImageUrl(row)" class="candidate-image" :src="candidateImageUrl(row)" fit="contain" :preview-src-list="[candidateImageUrl(row)!]" preview-teleported /><div v-else class="image-placeholder">暂无图片</div></template></el-table-column>
        <el-table-column label="SKU" min-width="130" fixed="left"><template #default="{ row }">{{ productValue(row, 'sku') }}</template></el-table-column>
        <el-table-column label="商品名称" min-width="220" show-overflow-tooltip fixed="left"><template #default="{ row }">{{ productValue(row, 'product_name') }}</template></el-table-column>
        <el-table-column v-for="column in visibleCandidateColumns" :key="column.key" :label="column.label" :min-width="column.minWidth" show-overflow-tooltip><template #default="{ row }">{{ candidateColumnValue(row, column) }}</template></el-table-column>
        <el-table-column label="确认状态" width="100" fixed="right"><template #default="{ row }"><el-tag :type="row.confirmation ? 'success' : 'info'">{{ row.confirmation ? '已确认' : '待确认' }}</el-tag></template></el-table-column>
      </el-table>
      <el-pagination v-model:current-page="candidatePage" v-model:page-size="candidatePageSize" :page-sizes="[50, 100, 200]" :total="candidateTotal" layout="total, sizes, prev, pager, next, jumper" @current-change="changeCandidatePage" @size-change="changeCandidatePageSize" />
    </el-card>
    <el-card v-if="run"><template #header><div class="card-header"><strong>单品与组合套装</strong><el-button :disabled="!selectionEditable" @click="openPackage">组成套装</el-button></div></template><el-alert title="人工确认的单品会直接生成 PPT 页；套装用于将多件商品合成一页。" type="info" :closable="false" /><div class="package-grid"><article v-for="item in packages" :key="item.id" class="package-card"><b>{{ item.name }}</b><span>{{ item.items.length }} 种商品 · 总价 {{ formatMoney(item.total_price) }}</span></article><el-empty v-if="packages.length === 0" description="暂未组成套装" /></div></el-card>
    <el-card v-if="run"><template #header><div class="card-header"><strong>生成可编辑 PPT</strong><el-button type="primary" :disabled="!canGenerate" :loading="acting" @click="generatePpt">生成系统 PPT</el-button></div></template><el-table :data="generations"><el-table-column prop="created_at" label="生成时间" min-width="180" /><el-table-column prop="status" label="状态" width="120" /><el-table-column prop="error" label="结果说明" min-width="260" /><el-table-column label="文件" width="110"><template #default="{ row }"><el-button v-if="row.status === 'SUCCEEDED'" link type="primary" @click="download(row)">下载 PPTX</el-button></template></el-table-column></el-table></el-card>
    <el-dialog v-model="packageVisible" title="组合商品套装" width="min(720px, 94vw)"><el-form label-position="top"><el-form-item label="套装名称 *"><el-input v-model="packageForm.name" /></el-form-item><el-form-item label="价格档位"><el-input v-model="packageForm.price_tier" type="number" /></el-form-item><el-form-item label="组套说明"><el-input v-model="packageForm.reason" type="textarea" /></el-form-item><el-form-item label="选择商品及数量"><div class="quantity-list"><div v-for="item in confirmed" :key="item.id"><span>{{ productValue(item, 'product_name') }}</span><el-input-number v-model="packageForm.quantities[item.id]" :min="0" :max="9999" /></div></div></el-form-item></el-form><template #footer><el-button @click="packageVisible = false">取消</el-button><el-button type="primary" :loading="acting" @click="createPackage">保存套装</el-button></template></el-dialog>
  </div>
</template>

<style scoped>
.workspace{display:grid;gap:18px}.workspace>header{display:flex;justify-content:space-between;gap:20px;padding:24px 28px;border-radius:14px;background:linear-gradient(135deg,#edf5ff,#f2f8f5)}.workspace h1{margin:4px 0}.workspace header p{margin:0;color:#2670ca;font-weight:700}.actions,.card-header,.selection-actions,.price-band,.band-tags{display:flex;align-items:center;flex-wrap:wrap;gap:12px}.card-header{justify-content:space-between}.muted{color:#909399;font-size:13px}.recommendation-config{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 18px}.recommendation-config .el-form-item:nth-child(2),.recommendation-config .el-alert{grid-column:1/-1}.price-bands{display:grid;gap:8px}.price-band .el-input{max-width:180px}.band-tags{margin-bottom:12px}.el-pagination{justify-content:flex-end;margin-top:16px}.column-picker{display:grid;grid-template-columns:1fr 1fr}.candidate-image{width:72px;height:72px}.image-placeholder{display:grid;place-items:center;width:72px;height:72px;color:#909399;background:#f5f7fa;border-radius:4px;font-size:12px}.package-grid,.quantity-list{display:grid;gap:10px;margin-top:14px}.package-card,.quantity-list>div{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:13px;border:1px solid #e4e7ed;border-radius:8px}@media(max-width:900px){.recommendation-config{grid-template-columns:1fr}.workspace>header{flex-direction:column}}
</style>
