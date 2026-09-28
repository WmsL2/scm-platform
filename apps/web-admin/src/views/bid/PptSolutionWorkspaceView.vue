<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useRoute, useRouter } from "vue-router"
import { bidApi } from "../../api/bid"
import { pptSolutionApi } from "../../api/pptSolution"
import { recommendationApi } from "../../api/recommendation"
import { HttpError } from "../../shared/http"
import type { BidProjectDetail } from "../../types/bid"
import type { PptGenerationTask, PptPackage } from "../../types/pptSolution"
import { RUN_STATUS_LABELS, type RecommendationCandidate, type RecommendationRun } from "../../types/recommendation"

const route = useRoute()
const router = useRouter()
const projectId = String(route.params.id)
const loading = ref(false)
const acting = ref(false)
const project = ref<BidProjectDetail>()
const run = ref<RecommendationRun | null>(null)
const packages = ref<PptPackage[]>([])
const generations = ref<PptGenerationTask[]>([])
const checked = ref<string[]>([])
const packageVisible = ref(false)
const packageForm = reactive({ name: "", price_tier: "", reason: "", quantities: {} as Record<string, number> })
let generationTimer: ReturnType<typeof setInterval> | undefined

const candidates = computed(() => run.value?.candidates ?? [])
const confirmed = computed(() => candidates.value.filter((item) => item.confirmation))
const unconfirmed = computed(() => candidates.value.filter((item) => !item.confirmation))
const editable = computed(() => project.value?.status === "SELECTING")
const canComplete = computed(() => editable.value && confirmed.value.length > 0)
const canGenerate = computed(() => Boolean(run.value && ["READY", "EXPORTED"].includes(project.value?.status ?? "") && ["CONFIRMED", "EXPORTED"].includes(run.value.status)))

function text(value: unknown): string { return value == null ? "—" : String(value) }
function nameOf(item: RecommendationCandidate): string { return text(item.product_snapshot.product_name) }
function modelOf(item: RecommendationCandidate): string { return [item.product_snapshot.brand, item.product_snapshot.model].filter(Boolean).join(" / ") || "—" }
function priceOf(item: RecommendationCandidate): string { return text(item.confirmation?.campaign_price ?? item.price_snapshot.agreement_price ?? item.price_snapshot.jd_price) }
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
    const history = await recommendationApi.runs(projectId)
    run.value = history[0] ? await recommendationApi.run(history[0].id, 1, 100) : null
    if (run.value) packages.value = await pptSolutionApi.packages(run.value.id)
    generations.value = await pptSolutionApi.generations(projectId)
  } catch (error) {
    ElMessage.error(messageFor(error, "加载 PPT 方案失败"))
  } finally { loading.value = false }
}

async function startRun(): Promise<void> {
  acting.value = true
  try {
    run.value = await recommendationApi.start(projectId)
    await load()
    if (run.value?.status === "FAILED") ElMessage.error(run.value.error || "Kimi 推荐执行失败")
    else ElMessage.success("商品推荐已生成，请人工选择")
  } catch (error) { ElMessage.error(messageFor(error, "生成推荐失败")) }
  finally { acting.value = false }
}

async function confirmCandidate(candidate: RecommendationCandidate): Promise<void> {
  acting.value = true
  try {
    await recommendationApi.confirm(candidate.id, {})
    await load()
  } catch (error) { ElMessage.error(messageFor(error, "确认商品失败")) }
  finally { acting.value = false }
}

async function removeCandidate(candidate: RecommendationCandidate): Promise<void> {
  acting.value = true
  try { await recommendationApi.removeConfirmation(candidate.id); await load() }
  catch (error) { ElMessage.error(messageFor(error, "移除商品失败")) }
  finally { acting.value = false }
}

async function confirmChecked(): Promise<void> {
  if (!run.value || checked.value.length === 0) return
  acting.value = true
  try { await recommendationApi.confirmMany(run.value.id, checked.value); checked.value = []; await load() }
  catch (error) { ElMessage.error(messageFor(error, "批量确认失败")) }
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
  try { await recommendationApi.completeSelection(projectId, run.value.id); await load(); ElMessage.success("选品已完成，可以生成 PPT") }
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

async function generatePpt(useDefaultTemplate: boolean): Promise<void> {
  if (!run.value) return
  acting.value = true
  try {
    const task = await pptSolutionApi.generate(projectId, run.value.id, useDefaultTemplate)
    generations.value = [task, ...generations.value.filter((item) => item.id !== task.id)]
    startGenerationPolling()
    ElMessage.success("PPT 已进入后台生成，可继续处理其他页面")
  } catch (error) { ElMessage.error(messageFor(error, "PPT 生成失败")) }
  finally { acting.value = false }
}

function startGenerationPolling(): void {
  if (generationTimer) return
  generationTimer = setInterval(async () => {
    generations.value = await pptSolutionApi.generations(projectId)
    if (!generations.value.some((item) => ["QUEUED", "RUNNING"].includes(item.status))) {
      clearInterval(generationTimer)
      generationTimer = undefined
    }
  }, 3000)
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
      <div class="hero-actions"><el-button @click="router.push('/bid-projects')">返回项目</el-button><el-button v-if="!run || ['FAILED', 'NO_CANDIDATES', 'NEEDS_INPUT'].includes(run.status)" type="primary" :loading="acting" @click="startRun">{{ run ? "重新生成推荐" : "生成商品推荐" }}</el-button><el-button v-if="editable" type="success" :disabled="!canComplete" :loading="acting" @click="completeSelection">完成选品</el-button><el-button v-else-if="canGenerate" @click="reopenSelection">返回调整选品</el-button></div>
    </header>
    <el-alert v-if="run?.error" :title="run.error" :type="run.status === 'FAILED' ? 'error' : 'warning'" show-icon :closable="false" />
    <el-card v-if="run"><template #header><div class="card-title"><strong>AI 推荐与人工选品</strong><el-tag>{{ RUN_STATUS_LABELS[run.status] }}</el-tag></div></template>
      <div class="selection-grid">
        <section><div class="section-title"><div><b>AI 推荐候选</b><small> Kimi 根据甲方需求推荐，最终由人工决定</small></div><el-button type="primary" :disabled="!editable || checked.length === 0" @click="confirmChecked">添加选中（{{ checked.length }}）</el-button></div>
          <el-checkbox-group v-model="checked" class="product-list"><article v-for="item in unconfirmed" :key="item.id" class="product-card"><el-checkbox :value="item.id" :disabled="!editable" /><div><b>{{ nameOf(item) }}</b><p>{{ modelOf(item) }}</p><p class="reason">{{ item.reason }}</p></div><div class="price">¥ {{ priceOf(item) }}<el-button link type="primary" :disabled="!editable" @click="confirmCandidate(item)">添加</el-button></div></article><el-empty v-if="unconfirmed.length === 0" description="暂无待选候选" /></el-checkbox-group>
        </section>
        <section><div class="section-title"><div><b>人工已选商品</b><small> {{ confirmed.length }} 件</small></div><el-button :disabled="!editable || confirmed.length < 2" @click="openPackage">组成套装</el-button></div>
          <div class="product-list"><article v-for="item in confirmed" :key="item.id" class="product-card selected"><div><b>{{ nameOf(item) }}</b><p>{{ modelOf(item) }}</p></div><div class="price">¥ {{ priceOf(item) }}<el-button link type="danger" :disabled="!editable" @click="removeCandidate(item)">移除</el-button></div></article><el-empty v-if="confirmed.length === 0" description="从左侧添加商品" /></div>
        </section>
      </div>
    </el-card>
    <el-card v-if="run"><template #header><div class="card-title"><strong>组合套装</strong><span>套装总价不能超过价格档位</span></div></template><div class="package-grid"><article v-for="item in packages" :key="item.id" class="package-card"><div><b>{{ item.name }}</b><p>{{ item.items.length }} 种商品 · 总价 ¥{{ item.total_price }} · 档位 {{ item.price_tier ? `¥${item.price_tier}` : '未指定' }}</p></div><el-button v-if="editable" link type="danger" @click="removePackage(item)">删除</el-button></article><el-empty v-if="packages.length === 0" description="暂未组合套装；单品也可以直接生成 PPT" /></div></el-card>
    <el-card v-if="run"><template #header><div class="card-title"><strong>生成可编辑 PPT</strong><div><el-button :disabled="!canGenerate" :loading="acting" @click="generatePpt(false)">按项目模板生成</el-button><el-button type="primary" :disabled="!canGenerate" :loading="acting" @click="generatePpt(true)">使用系统默认模板生成</el-button></div></div></template><el-table :data="generations"><el-table-column prop="created_at" label="生成时间" min-width="180" /><el-table-column prop="status" label="状态" /><el-table-column prop="provider" label="生成服务" /><el-table-column prop="error" label="结果说明" min-width="260" /><el-table-column label="文件"><template #default="{ row }"><el-button v-if="row.status === 'SUCCEEDED'" link type="primary" @click="download(row)">下载 PPTX</el-button></template></el-table-column></el-table></el-card>
    <el-dialog v-model="packageVisible" title="组合商品套装" width="min(720px, 94vw)"><el-form label-position="top"><el-form-item label="套装名称 *"><el-input v-model="packageForm.name" /></el-form-item><el-form-item label="价格档位"><el-input v-model="packageForm.price_tier" type="number" min="0" placeholder="例如 500" /></el-form-item><el-form-item label="组套说明"><el-input v-model="packageForm.reason" type="textarea" /></el-form-item><el-form-item label="选择商品及数量"><div class="quantity-list"><div v-for="item in confirmed" :key="item.id"><span>{{ nameOf(item) }}</span><el-input-number v-model="packageForm.quantities[item.id]" :min="0" :max="9999" /></div></div></el-form-item></el-form><template #footer><el-button @click="packageVisible = false">取消</el-button><el-button type="primary" :loading="acting" @click="createPackage">保存套装</el-button></template></el-dialog>
  </div>
</template>

<style scoped>
.ppt-page{display:grid;gap:18px}.hero{display:flex;justify-content:space-between;gap:24px;padding:24px 28px;border-radius:14px;background:linear-gradient(120deg,#edf5ff,#f7f2ff)}.hero p{margin:0;color:#2670ca;font-weight:700}.hero h1{margin:5px 0}.hero span{color:#606266;line-height:1.6}.hero-actions,.card-title,.section-title{display:flex;align-items:center;justify-content:space-between;gap:12px}.card-title span,.section-title small{color:#909399;font-weight:400}.selection-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.selection-grid section{min-width:0;padding:14px;border:1px solid #e4e7ed;border-radius:10px;background:#fafcff}.product-list{display:grid;gap:10px;margin-top:14px}.product-card{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:12px;align-items:start;padding:14px;border:1px solid #dcdfe6;border-radius:9px;background:white}.product-card.selected{border-color:#91caff;background:#ecf5ff}.product-card p{margin:5px 0 0;color:#909399}.product-card .reason{color:#606266}.price{display:grid;justify-items:end;gap:8px;color:#e66b1d;font-weight:700}.package-grid,.quantity-list{display:grid;gap:10px}.package-card,.quantity-list>div{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:13px;border:1px solid #e4e7ed;border-radius:8px}.package-card p{margin:5px 0 0;color:#909399}@media(max-width:900px){.selection-grid{grid-template-columns:1fr}.hero{flex-direction:column}.hero-actions{justify-content:flex-start;flex-wrap:wrap}}
</style>
