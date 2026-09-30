<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useRoute, useRouter } from "vue-router"
import { bidApi } from "../../api/bid"
import { pptSolutionApi } from "../../api/pptSolution"
import { recommendationApi } from "../../api/recommendation"
import { HttpError } from "../../shared/http"
import type { BidProjectDetail } from "../../types/bid"
import type { PptGenerationTask, PptPackage, PptPriceBandAvailability, PptRecommendationMode, PptSolutionPlan, PptSolutionPlanItem } from "../../types/pptSolution"
import { RUN_STATUS_LABELS, type RecommendationCandidate, type RecommendationRun } from "../../types/recommendation"

const route = useRoute()
const router = useRouter()
const projectId = String(route.params.id)
const loading = ref(false)
const acting = ref(false)
const project = ref<BidProjectDetail>()
const run = ref<RecommendationRun | null>(null)
const plans = ref<PptSolutionPlan[]>([])
const planAvailability = ref<PptPriceBandAvailability[]>([])
const packages = ref<PptPackage[]>([])
const generations = ref<PptGenerationTask[]>([])
const packageVisible = ref(false)
const planDetailVisible = ref(false)
const selectedPlan = ref<PptSolutionPlan>()
const packageForm = reactive({ name: "", price_tier: "", reason: "", quantities: {} as Record<string, number> })
const recommendationConfig = reactive({ recommendation_mode: "MIXED" as PptRecommendationMode, price_bands: [{ min_price: null as string | null, max_price: "50" }], candidate_count_per_band: 10, plan_count_per_band: 3, fulfillment_deadline: null as string | null })
let generationTimer: ReturnType<typeof setInterval> | undefined

const candidates = computed(() => run.value?.candidates ?? [])
const candidatePoolTotal = computed(() => run.value?.candidate_page?.total ?? 0)
const confirmed = computed(() => candidates.value.filter((item) => item.confirmation))
const packagedCandidateIds = computed(() => new Set(packages.value.flatMap((item) => item.items.map((line) => line.candidate_id))))
const directPptCount = computed(() => confirmed.value.filter((item) => !packagedCandidateIds.value.has(item.id)).length)
const editable = computed(() => project.value?.status === "SELECTING")
const canComplete = computed(() => editable.value && (run.value?.candidate_page?.confirmed_total ?? 0) > 0)
const canGenerate = computed(() => Boolean(run.value && ["READY", "EXPORTED"].includes(project.value?.status ?? "") && ["CONFIRMED", "EXPORTED"].includes(run.value.status)))

function nonEmptyText(value: unknown): string | null { const result = String(value ?? "").trim(); return result || null }
function nameOf(item: RecommendationCandidate): string { return nonEmptyText(item.product_snapshot.product_name) || `商品 ${item.product_id.slice(0, 8)}` }
function formatMoney(value: unknown): string {
  const raw = nonEmptyText(value)
  if (!raw) return "—"
  const match = raw.match(/^(-?)(\d+)(?:\.(\d+))?$/)
  if (!match) return raw
  const integer = match[2].replace(/\B(?=(\d{3})+(?!\d))/g, ",")
  return `${match[1]}${integer}.${(match[3] ?? "").slice(0, 2).padEnd(2, "0")}`
}
function planItemValue(item: PptSolutionPlanItem, key: string): string {
  const value = item.product_snapshot[key] ?? item.price_snapshot[key]
  return value === null || value === undefined || value === "" ? "-" : String(value)
}
function messageFor(error: unknown, fallback: string): string { return error instanceof HttpError ? error.response.message : fallback }

async function load(): Promise<void> {
  loading.value = true
  try {
    project.value = await bidApi.get(projectId)
    if (project.value.project_type !== "PPT_SOLUTION") {
      ElMessage.warning("该项目不是类型 5 PPT 方案项目")
      await router.replace(`/bid-projects/${projectId}`)
      return
    }
    const savedConfig = await pptSolutionApi.config(projectId)
    if (savedConfig) Object.assign(recommendationConfig, { recommendation_mode: savedConfig.recommendation_mode, price_bands: savedConfig.price_bands, candidate_count_per_band: savedConfig.candidate_count_per_band, plan_count_per_band: savedConfig.plan_count_per_band, fulfillment_deadline: savedConfig.fulfillment_deadline })
    const history = await recommendationApi.runs(projectId)
    run.value = history[0] ? await recommendationApi.run(history[0].id, 1, 100) : null
    if (run.value) {
      const [loadedPlans, loadedPackages, loadedAvailability] = await Promise.all([
        pptSolutionApi.plans(run.value.id),
        pptSolutionApi.packages(run.value.id),
        pptSolutionApi.planAvailability(run.value.id),
      ])
      plans.value = loadedPlans
      packages.value = loadedPackages
      planAvailability.value = loadedAvailability
    } else {
      plans.value = []
      packages.value = []
      planAvailability.value = []
    }
    generations.value = await pptSolutionApi.generations(projectId)
  } catch (error) {
    ElMessage.error(messageFor(error, "加载 PPT 方案失败"))
  } finally { loading.value = false }
}

async function startRun(): Promise<void> {
  acting.value = true
  try {
    await pptSolutionApi.saveConfig(projectId, recommendationConfig)
    run.value = await recommendationApi.start(projectId)
    await load()
    if (run.value?.status === "FAILED") ElMessage.error(run.value.error || "AI 推荐执行失败")
    else ElMessage.success("推品方案已生成，请选择并确认商品")
  } catch (error) { ElMessage.error(messageFor(error, "生成推荐失败")) }
  finally { acting.value = false }
}

function addPriceBand(): void { recommendationConfig.price_bands.push({ min_price: null, max_price: "" }) }
function removePriceBand(index: number): void { if (recommendationConfig.price_bands.length > 1) recommendationConfig.price_bands.splice(index, 1) }

function openPlanDetail(plan: PptSolutionPlan): void {
  selectedPlan.value = plan
  planDetailVisible.value = true
}

async function confirmPlan(plan: PptSolutionPlan): Promise<void> {
  if (!run.value) return
  acting.value = true
  try {
    await recommendationApi.confirmMany(run.value.id, plan.candidate_ids)
    await load()
    ElMessage.success(`已确认方案“${plan.name}”中的 ${plan.candidate_ids.length} 件商品`)
  } catch (error) { ElMessage.error(messageFor(error, "确认方案商品失败")) }
  finally { acting.value = false }
}

function openPackage(): void {
  if (confirmed.value.length < 2) {
    ElMessage.warning("至少确认两件商品后才能组成套装")
    return
  }
  packageForm.name = ""
  packageForm.price_tier = ""
  packageForm.reason = ""
  packageForm.quantities = Object.fromEntries(confirmed.value.map((item) => [item.id, 0]))
  packageVisible.value = true
}

async function createPackage(): Promise<void> {
  const items = Object.entries(packageForm.quantities).filter(([, quantity]) => quantity > 0).map(([candidate_id, quantity]) => ({ candidate_id, quantity }))
  if (!packageForm.name.trim()) {
    ElMessage.warning("请填写套装名称")
    return
  }
  if (items.length < 2) {
    ElMessage.warning("一个套装至少包含两种商品")
    return
  }
  acting.value = true
  try {
    await pptSolutionApi.createPackage(run.value!.id, { name: packageForm.name.trim(), price_tier: packageForm.price_tier || null, reason: packageForm.reason.trim() || null, items })
    packageVisible.value = false
    await load()
    ElMessage.success("套装已保存")
  } catch (error) { ElMessage.error(messageFor(error, "保存套装失败")) }
  finally { acting.value = false }
}

async function removePackage(item: PptPackage): Promise<void> {
  try { await ElMessageBox.confirm(`确认删除套装“${item.name}”？`, "删除套装", { type: "warning" }) }
  catch { return }
  await pptSolutionApi.removePackage(item.id)
  await load()
}

async function completeSelection(): Promise<void> {
  if (!run.value) return
  acting.value = true
  try {
    await recommendationApi.completeSelection(projectId, run.value.id)
    await load()
    ElMessage.success("选品已完成，可以在下方生成系统 PPT")
  }
  catch (error) { ElMessage.error(messageFor(error, "完成选品失败")) }
  finally { acting.value = false }
}

async function reopenSelection(): Promise<void> {
  if (!run.value) return
  acting.value = true
  try { await recommendationApi.reopenSelection(projectId, run.value.id); await load() }
  catch (error) { ElMessage.error(messageFor(error, "返回选品失败")) }
  finally { acting.value = false }
}

async function generatePpt(): Promise<void> {
  if (!run.value) return
  acting.value = true
  try {
    const task = await pptSolutionApi.generate(projectId, run.value.id)
    generations.value = [task, ...generations.value.filter((item) => item.id !== task.id)]
    startGenerationPolling()
    ElMessage.success("正在按系统默认模板生成 PPT")
  } catch (error) { ElMessage.error(messageFor(error, "PPT 生成失败")) }
  finally { acting.value = false }
}

function startGenerationPolling(): void {
  if (generationTimer) return
  void refreshGenerations()
  generationTimer = setInterval(async () => {
    await refreshGenerations()
    if (!generations.value.some((item) => ["QUEUED", "RUNNING"].includes(item.status))) {
      clearInterval(generationTimer)
      generationTimer = undefined
    }
  }, 3000)
}

async function refreshGenerations(): Promise<void> {
  try {
    const previous = new Map(generations.value.map((item) => [item.id, item.status]))
    const latest = await pptSolutionApi.generations(projectId)
    generations.value = latest
    for (const task of latest) {
      if (previous.get(task.id) === task.status) continue
      if (task.status === "SUCCEEDED") ElMessage.success("PPT 已生成，请在本模块的对应记录下载")
      if (task.status === "FAILED") ElMessage.error(task.error || "PPT 生成失败，请检查后端日志")
    }
  } catch (error) { ElMessage.error(messageFor(error, "获取 PPT 生成状态失败")) }
}

async function download(task: PptGenerationTask): Promise<void> {
  if (!task.output_file_id) return
  const blob = await pptSolutionApi.download(task.id, task.output_file_id)
  const link = document.createElement("a")
  link.href = URL.createObjectURL(blob)
  link.download = `${project.value?.project_name ?? "PPT方案"}.pptx`
  link.click()
  URL.revokeObjectURL(link.href)
}

onMounted(async () => { await load(); if (generations.value.some((item) => ["QUEUED", "RUNNING"].includes(item.status))) startGenerationPolling() })
onBeforeUnmount(() => { if (generationTimer) clearInterval(generationTimer) })
</script>

<template>
  <div v-loading="loading" class="ppt-page">
    <header class="hero">
      <div><p>TYPE 5 · PPT SOLUTION</p><h1>{{ project?.project_name || "PPT 方案" }}</h1><span>{{ project?.buyer_name }} · {{ project?.remark }}</span></div>
      <div class="hero-actions"><el-button @click="router.push('/bid-projects')">返回项目</el-button></div>
    </header>
    <el-alert v-if="run?.error" :title="run.error" :type="run.status === 'FAILED' ? 'error' : 'warning'" show-icon :closable="false" />
    <el-card v-if="!run || editable"><template #header><div class="card-title"><div><strong>推品配置</strong><span>先设置模式、价格档和生成数量，再生成推品方案</span></div></div></template>
      <el-form label-position="top" class="recommendation-config">
        <el-form-item label="推品方式"><el-radio-group v-model="recommendationConfig.recommendation_mode"><el-radio-button value="SINGLE">单品推品</el-radio-button><el-radio-button value="COMBINATION">组合推品</el-radio-button><el-radio-button value="MIXED">混合推品</el-radio-button></el-radio-group></el-form-item>
        <el-form-item label="价格档 / 价格区间"><div class="price-bands"><div v-for="(band, index) in recommendationConfig.price_bands" :key="index" class="price-band"><el-input v-model="band.min_price" type="number" min="0" placeholder="最低价（可空）" /><span>至</span><el-input v-model="band.max_price" type="number" min="0.01" placeholder="最高预算 *" /><el-button link type="danger" :disabled="recommendationConfig.price_bands.length === 1" @click="removePriceBand(index)">删除</el-button></div><el-button @click="addPriceBand">新增价格档</el-button></div></el-form-item>
        <el-form-item label="每个方案商品数量"><el-input-number v-model="recommendationConfig.candidate_count_per_band" :min="1" :max="500" /></el-form-item>
        <el-form-item label="每档生成方案数"><el-input-number v-model="recommendationConfig.plan_count_per_band" :min="1" :max="20" /></el-form-item>
        <el-form-item label="履约截止日"><el-date-picker v-model="recommendationConfig.fulfillment_deadline" type="date" value-format="YYYY-MM-DD" placeholder="例如 2027-12-31" /></el-form-item>
        <el-alert title="价格档按每件商品的协议价筛选，不计算方案总价；每个方案会从完整商品池中组织指定数量的商品。履约截止日会进入方案说明，仍需人工核验商品的实际履约能力。" type="info" :closable="false" />
      </el-form>
    </el-card>
    <el-card><template #header><div class="card-title"><div><strong>推品方案与人工选品</strong><el-tag v-if="run">{{ RUN_STATUS_LABELS[run.status] }}</el-tag></div><div class="module-actions"><el-button v-if="!run || editable" type="primary" :loading="acting" @click="startRun">{{ run ? "重新生成推品" : "生成推品" }}</el-button><el-button v-if="editable" type="success" :disabled="!canComplete" :loading="acting" @click="completeSelection">完成选品</el-button><el-button v-else-if="canGenerate" @click="reopenSelection">返回调整选品</el-button></div></div></template>
      <el-empty v-if="!run" description="请先生成推品方案"><el-button type="primary" :loading="acting" @click="startRun">生成推品</el-button></el-empty>
      <div v-else>
        <section class="plan-section"><div class="plan-section-title"><b>本次推品方案</b><small>已冻结 {{ candidatePoolTotal }} 件完整候选商品；价格档按每件商品的协议价筛选，每个方案含指定数量的商品。</small></div><div v-if="planAvailability.length" class="plan-availability"><el-tag v-for="band in planAvailability" :key="band.price_band_index" :type="band.can_generate ? 'success' : 'warning'">{{ band.message }}</el-tag></div><div v-if="plans.length" class="plan-grid"><article v-for="plan in plans" :key="plan.id" class="plan-card"><div class="plan-card-head"><strong>{{ plan.name }}</strong><el-tag :type="plan.plan_type === 'SINGLE' ? 'primary' : 'success'">{{ plan.plan_type === 'SINGLE' ? '单品方案' : '组合方案' }}</el-tag></div><p>{{ plan.summary }}</p><div class="plan-actions"><el-button @click="openPlanDetail(plan)">具体商品详情（{{ plan.items.length }}）</el-button><el-button type="primary" :disabled="!editable" :loading="acting" @click="confirmPlan(plan)">确认本方案商品</el-button></div></article></div><el-alert v-else-if="['WAITING_CONFIRMATION', 'CONFIRMED', 'EXPORTED'].includes(run.status)" :title="planAvailability.some((band) => band.can_generate) ? '存在满足数量要求的价格档，但尚未生成方案；请查看上方失败原因后重新生成。' : '没有价格档满足每个方案所需商品数量；请按上方每档真实数量调整价格档或每方案商品数量。'" type="warning" :closable="false" /><el-empty v-else :description="run.status === 'FAILED' ? '本次推品执行失败，请修改配置后重新生成。' : '正在生成推品方案，请稍候。'" /></section>
      </div>
    </el-card>
    <el-card v-if="run"><template #header><div class="card-title"><strong>单品与组合套装</strong><span>组套仅用于把多件商品合成一页，不是生成 PPT 的前置条件</span></div></template><el-alert :title="`当前有 ${directPptCount} 件人工确认单品会各生成 1 页 PPT；已组成套装的商品按套装生成。`" type="info" show-icon :closable="false" /><div class="package-grid"><article v-for="item in packages" :key="item.id" class="package-card"><div><b>{{ item.name }}</b><p>{{ item.items.length }} 种商品 · 总价 ¥{{ formatMoney(item.total_price) }} · 档位 {{ item.price_tier ? `¥${formatMoney(item.price_tier)}` : '未指定' }}</p></div><el-button v-if="editable" link type="danger" @click="removePackage(item)">删除</el-button></article><el-empty v-if="packages.length === 0" description="暂未组成套装；所有人工确认单品都会直接生成各自的 PPT 页" /></div></el-card>
    <el-card v-if="run"><template #header><div class="card-title"><div><strong>生成可编辑 PPT</strong><span>固定使用系统默认模板</span></div><el-button type="primary" :disabled="!canGenerate" :loading="acting" @click="generatePpt">生成系统 PPT</el-button></div></template><el-table :data="generations"><el-table-column prop="created_at" label="生成时间" min-width="180" /><el-table-column label="状态" min-width="110"><template #default="{ row }"><el-tag :type="row.status === 'SUCCEEDED' ? 'success' : row.status === 'FAILED' ? 'danger' : 'warning'">{{ row.status === 'SUCCEEDED' ? '已生成' : row.status === 'FAILED' ? '生成失败' : '生成中' }}</el-tag></template></el-table-column><el-table-column prop="provider" label="生成服务" min-width="190" /><el-table-column prop="error" label="结果说明" min-width="260" /><el-table-column label="文件" min-width="130"><template #default="{ row }"><el-button v-if="row.status === 'SUCCEEDED'" link type="primary" @click="download(row)">下载 PPTX</el-button><span v-else>—</span></template></el-table-column></el-table></el-card>
    <el-dialog v-model="planDetailVisible" :title="selectedPlan?.name ?? '方案商品详情'" width="min(1200px, 94vw)"><el-table :data="selectedPlan?.items ?? []" max-height="560"><el-table-column prop="rank" label="序号" width="80" /><el-table-column label="SKU" min-width="150"><template #default="{ row }">{{ planItemValue(row, 'sku') }}</template></el-table-column><el-table-column label="商品名称" min-width="260" show-overflow-tooltip><template #default="{ row }">{{ planItemValue(row, 'product_name') }}</template></el-table-column><el-table-column label="品牌" min-width="130"><template #default="{ row }">{{ planItemValue(row, 'brand') }}</template></el-table-column><el-table-column label="型号" min-width="170" show-overflow-tooltip><template #default="{ row }">{{ planItemValue(row, 'model') }}</template></el-table-column><el-table-column label="三级类目" min-width="150"><template #default="{ row }">{{ planItemValue(row, 'category_level3_name') }}</template></el-table-column><el-table-column label="京东价" min-width="120"><template #default="{ row }">¥ {{ formatMoney(row.price_snapshot.jd_price) }}</template></el-table-column><el-table-column label="协议价" min-width="120"><template #default="{ row }">¥ {{ formatMoney(row.price_snapshot.agreement_price) }}</template></el-table-column></el-table><template #footer><el-button @click="planDetailVisible = false">关闭</el-button><el-button v-if="selectedPlan && editable" type="primary" :loading="acting" @click="confirmPlan(selectedPlan)">确认本方案商品</el-button></template></el-dialog>
    <el-dialog v-model="packageVisible" title="组合商品套装" width="min(720px, 94vw)"><el-form label-position="top"><el-form-item label="套装名称 *"><el-input v-model="packageForm.name" /></el-form-item><el-form-item label="价格档位"><el-input v-model="packageForm.price_tier" type="number" min="0" placeholder="例如 500" /></el-form-item><el-form-item label="组套说明"><el-input v-model="packageForm.reason" type="textarea" /></el-form-item><el-form-item label="选择商品及数量"><div class="quantity-list"><div v-for="item in confirmed" :key="item.id"><span>{{ nameOf(item) }}</span><el-input-number v-model="packageForm.quantities[item.id]" :min="0" :max="9999" /></div></div></el-form-item></el-form><template #footer><el-button @click="packageVisible = false">取消</el-button><el-button type="primary" :loading="acting" @click="createPackage">保存套装</el-button></template></el-dialog>
  </div>
</template>

<style scoped>
.ppt-page{display:grid;gap:18px}.hero{display:flex;justify-content:space-between;gap:24px;padding:24px 28px;border-radius:14px;background:linear-gradient(120deg,#edf5ff,#f7f2ff)}.hero p{margin:0;color:#2670ca;font-weight:700}.hero h1{margin:5px 0}.hero span{color:#606266;line-height:1.6}.hero-actions,.card-title,.module-actions,.plan-section-title,.plan-card-head,.plan-actions,.plan-availability{display:flex;align-items:center;gap:12px}.card-title,.plan-section-title,.plan-card-head{justify-content:space-between}.module-actions,.plan-actions{justify-content:flex-end;flex-wrap:wrap}.card-title>div:first-child{display:flex;align-items:center;gap:10px}.card-title span,.plan-section-title small{color:#909399;font-weight:400}.recommendation-config{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 18px}.recommendation-config .el-form-item:nth-child(2),.recommendation-config .el-alert{grid-column:1/-1}.price-bands{display:grid;gap:8px}.price-band{display:flex;align-items:center;gap:8px}.price-band .el-input{max-width:180px}.plan-section{margin-bottom:20px}.plan-section-title{margin-bottom:12px}.plan-availability{flex-wrap:wrap;margin:0 0 12px}.plan-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}.plan-card{display:grid;gap:12px;padding:16px;border:1px solid #d9ecff;border-radius:8px;background:#f8fbff}.plan-card p{margin:0;color:#606266}.plan-actions{justify-content:flex-start}.package-grid,.quantity-list{display:grid;gap:10px;margin-top:14px}.package-card,.quantity-list>div{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:13px;border:1px solid #e4e7ed;border-radius:8px}.package-card p{margin:5px 0 0;color:#909399}@media(max-width:900px){.recommendation-config{grid-template-columns:1fr}.hero,.plan-section-title{flex-direction:column}.hero-actions,.module-actions,.plan-actions{justify-content:flex-start;flex-wrap:wrap}.price-band{flex-wrap:wrap}}
</style>
