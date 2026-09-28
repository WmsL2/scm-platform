<script setup lang="ts">
import { onMounted, reactive, ref } from "vue"
import { ElMessage } from "element-plus"
import type { UploadInstance } from "element-plus"
import { useRoute, useRouter } from "vue-router"
import { bidApi } from "../../api/bid"
import { HttpError } from "../../shared/http"
import { useExcelImportNavigationLock } from "../../shared/import/excelImportNavigationLock"
import OperationDuration from "../../shared/operation/OperationDuration.vue"
import { useOperationTimer } from "../../shared/operation/useOperationTimer"
import { useAuthStore } from "../../stores/auth"
import {
  IMPORT_STATUS_LABELS,
  PROJECT_STATUS_LABELS,
  PROJECT_TYPE_LABELS,
  type BidProjectListItem,
  type BidProjectStatus,
  type BidProjectType,
} from "../../types/bid"

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const operationTimer = useOperationTimer()
const importNavigationLock = useExcelImportNavigationLock(operationTimer)
const projects = ref<BidProjectListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(50)
const filters = reactive({ keyword: "", status: undefined as BidProjectStatus | undefined })
const createVisible = ref(false)
const businessFile = ref<File>()
const recommendationTemplate = ref<File>()
const businessUpload = ref<UploadInstance>()
const recommendationUpload = ref<UploadInstance>()
const form = reactive({
  project_type: "FILTER_RECOMMENDATION" as BidProjectType,
  project_name: "",
  buyer_name: "",
  start_at: "",
  deadline_at: "",
  remark: "",
})

const projectTypeOptions: Array<{ value: BidProjectType; title: string; description: string; disabled?: boolean }> = [
  { value: "FILTER_RECOMMENDATION", title: "类型 1–3 · 条件筛选推品", description: "上传客户需求 Excel，按明确条件匹配商品。" },
  { value: "FREE_RECOMMENDATION", title: "类型 4 · 自由推品 Agent", description: "填写场景需求并上传本项目的推荐结果模板。" },
  { value: "PPT_SOLUTION", title: "类型 5 · PPT 方案", description: "本期暂未开放。", disabled: true },
]

async function load(target = page.value) {
  loading.value = true
  try {
    const result = await bidApi.list({
      page: target,
      page_size: pageSize.value,
      keyword: filters.keyword.trim() || undefined,
      status: filters.status,
    })
    projects.value = result.items
    total.value = result.total
    page.value = result.page
  } catch (error) {
    ElMessage.error(messageFor(error, "加载项目列表失败"))
  } finally {
    loading.value = false
  }
}

function validateXlsx(candidate: File): boolean {
  if (!candidate.name.toLowerCase().endsWith(".xlsx")) {
    ElMessage.error("目前仅支持 .xlsx 文件")
    return false
  }
  if (candidate.size > 25 * 1024 * 1024) {
    ElMessage.error("Excel 文件不能超过 25 MB")
    return false
  }
  return true
}

function chooseBusinessFile(upload: { raw: File }) {
  if (validateXlsx(upload.raw)) businessFile.value = upload.raw
}

function chooseRecommendationTemplate(upload: { raw: File }) {
  if (validateXlsx(upload.raw)) recommendationTemplate.value = upload.raw
}

function resetTypeFiles() {
  businessFile.value = undefined
  recommendationTemplate.value = undefined
  businessUpload.value?.clearFiles()
  recommendationUpload.value?.clearFiles()
}

function clearBusinessFile() {
  businessFile.value = undefined
  businessUpload.value?.clearFiles()
}

function clearRecommendationTemplate() {
  recommendationTemplate.value = undefined
  recommendationUpload.value?.clearFiles()
}

async function create() {
  if (!form.project_name.trim() || !form.buyer_name.trim()) {
    return ElMessage.error("请填写项目名称和需求方")
  }
  if (form.project_type === "FILTER_RECOMMENDATION" && !businessFile.value) {
    return ElMessage.error("请选择客户需求 Excel")
  }
  if (form.project_type === "FREE_RECOMMENDATION") {
    if (form.remark.trim().length < 20) return ElMessage.error("自由推品需求说明不能少于 20 个字符")
    if (!recommendationTemplate.value) return ElMessage.error("请选择自由推品结果模板")
  }
  if (form.start_at && form.deadline_at && form.start_at > form.deadline_at) {
    return ElMessage.error("开始时间不能晚于截止时间")
  }
  submitting.value = true
  importNavigationLock.start()
  try {
    const result = await operationTimer.measure("投标 Excel 导入", () => bidApi.create({
      ...form,
      project_name: form.project_name.trim(),
      buyer_name: form.buyer_name.trim(),
      remark: form.remark.trim(),
      file: businessFile.value,
      recommendation_template: recommendationTemplate.value,
    }))
    const isFree = result.project_type === "FREE_RECOMMENDATION"
    ElMessage.success(isFree ? "自由推品项目创建成功，请确认模板字段映射。" : result.import_status === "PARSED"
      ? "项目创建成功，Excel 已解析，可以开始商品匹配。"
      : result.import_status === "MAPPING_REQUIRED"
        ? "项目已创建，但当前 Excel 未识别到模板，需要完成模板配置。"
        : `项目已创建，但 Excel 解析失败：${result.import_error ?? "未知错误"}`)
    createVisible.value = false
    if (isFree) await router.push(`/bid-projects/${result.id}/recommendation`)
    else await load(1)
  } catch (error) {
    ElMessage.error(messageFor(error, "创建项目失败"))
  } finally {
    importNavigationLock.stop()
    submitting.value = false
  }
}

function messageFor(error: unknown, fallback: string): string {
  return error instanceof HttpError ? error.response.message : fallback
}

function projectTypeLabel(value: BidProjectType): string {
  return PROJECT_TYPE_LABELS[value]
}

onMounted(() => {
  void load()
  if (route.query.action === "create" && auth.hasPermission("bid:create")) {
    createVisible.value = true
    void router.replace("/bid-projects")
  }
})
</script>

<template>
  <div class="bid-page">
    <header>
      <div><p>BID PROJECTS</p><h1>投标与推品项目</h1><span>统一管理条件筛选推品与类型4自由推品项目。</span></div>
      <div class="header-actions">
        <el-button v-if="auth.hasPermission('bid:create')" type="primary" @click="createVisible = true">新建项目</el-button>
        <OperationDuration :timing="operationTimer.state" />
      </div>
    </header>
    <el-card>
      <el-form class="filter-form" @submit.prevent="load(1)">
        <el-form-item label="项目"><el-input v-model="filters.keyword" clearable placeholder="搜索项目编号或项目名称" @change="load(1)" /></el-form-item>
        <el-form-item label="状态"><el-select v-model="filters.status" clearable placeholder="全部状态" @change="load(1)"><el-option v-for="(label, key) in PROJECT_STATUS_LABELS" :key="key" :label="label" :value="key" /></el-select></el-form-item>
        <el-form-item><el-button type="primary" @click="load(1)">查询</el-button></el-form-item>
      </el-form>
    </el-card>
    <el-card>
      <el-table v-loading="loading" :data="projects">
        <el-table-column prop="project_code" label="项目编号" min-width="130" />
        <el-table-column prop="project_name" label="项目名称" min-width="180" />
        <el-table-column label="项目类型" min-width="150"><template #default="{ row }">{{ projectTypeLabel(row.project_type) }}</template></el-table-column>
        <el-table-column prop="buyer_name" label="需求方" min-width="150" />
        <el-table-column label="项目状态"><template #default="{ row }"><el-tag>{{ PROJECT_STATUS_LABELS[row.status] }}</el-tag></template></el-table-column>
        <el-table-column label="导入状态"><template #default="{ row }">{{ IMPORT_STATUS_LABELS[row.import_status] }}</template></el-table-column>
        <el-table-column prop="total_item_count" label="需求总数" />
        <el-table-column prop="processed_item_count" label="匹配处理数" />
        <el-table-column prop="start_at" label="开始时间" min-width="170" />
        <el-table-column prop="deadline_at" label="截止时间" min-width="170" />
        <el-table-column label="操作"><template #default="{ row }"><RouterLink :to="row.project_type === 'FREE_RECOMMENDATION' ? `/bid-projects/${row.id}/recommendation` : `/bid-projects/${row.id}`"><el-button link type="primary">详情</el-button></RouterLink></template></el-table-column>
      </el-table>
      <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :page-sizes="[20, 50, 100]" layout="total, sizes, prev, pager, next" :total="total" @current-change="load" @size-change="() => load(1)" />
    </el-card>

    <el-dialog v-model="createVisible" title="新建项目" width="min(900px, 94vw)" @closed="resetTypeFiles">
      <el-alert v-if="submitting" title="正在创建项目并分析模板，请稍候。" type="info" :closable="false" />
      <div class="type-grid">
        <button v-for="option in projectTypeOptions" :key="option.value" type="button" class="type-card" :class="{ active: form.project_type === option.value, disabled: option.disabled || (option.value === 'FREE_RECOMMENDATION' && !auth.hasPermission('recommendation:create')) }" :disabled="option.disabled || (option.value === 'FREE_RECOMMENDATION' && !auth.hasPermission('recommendation:create'))" @click="form.project_type = option.value; resetTypeFiles()">
          <strong>{{ option.title }}</strong><span>{{ option.description }}</span>
        </button>
      </div>
      <el-form label-position="top" class="create-project-form">
        <el-form-item label="项目名称 *"><el-input v-model="form.project_name" /></el-form-item>
        <el-form-item label="需求方 *"><el-input v-model="form.buyer_name" /></el-form-item>
        <el-form-item label="开始时间"><el-date-picker v-model="form.start_at" value-format="YYYY-MM-DDTHH:mm:ss" type="datetime" /></el-form-item>
        <el-form-item label="截止时间"><el-date-picker v-model="form.deadline_at" value-format="YYYY-MM-DDTHH:mm:ss" type="datetime" /></el-form-item>
        <el-form-item v-if="form.project_type === 'FILTER_RECOMMENDATION'" label="客户需求 Excel *" class="full">
          <div class="upload-control"><el-upload ref="businessUpload" :auto-upload="false" :limit="1" :show-file-list="false" accept=".xlsx" :on-change="chooseBusinessFile"><el-button>选择 .xlsx 文件</el-button></el-upload><div v-if="businessFile" class="selected-file"><span>{{ businessFile.name }}</span><el-button link type="danger" @click="clearBusinessFile">移除</el-button></div></div>
        </el-form-item>
        <el-form-item v-if="form.project_type === 'FREE_RECOMMENDATION'" label="自由推品结果模板 *" class="full">
          <div class="upload-control"><el-upload ref="recommendationUpload" :auto-upload="false" :limit="1" :show-file-list="false" accept=".xlsx" :on-change="chooseRecommendationTemplate"><el-button>选择 .xlsx 模板</el-button></el-upload><div v-if="recommendationTemplate" class="selected-file"><span>{{ recommendationTemplate.name }}</span><el-button link type="danger" @click="clearRecommendationTemplate">移除</el-button></div></div>
        </el-form-item>
        <el-form-item :label="form.project_type === 'FREE_RECOMMENDATION' ? '场景需求说明 *（至少20字）' : '备注'" class="full">
          <el-input v-model="form.remark" type="textarea" :rows="4" maxlength="5000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer><OperationDuration :timing="operationTimer.state" /><el-button @click="createVisible = false">取消</el-button><el-button type="primary" :loading="submitting" @click="create">创建项目</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.bid-page { display: grid; gap: 18px; }
header { display: flex; justify-content: space-between; align-items: start; padding: 24px 28px; border-radius: 14px; background: #edf5ff; }
h1 { margin: 4px 0; } header p { margin: 0; color: #2670ca; font-weight: 700; }
.header-actions { display: flex; flex-direction: column; align-items: flex-end; }
.filter-form { display: grid; grid-template-columns: minmax(280px, 420px) 180px auto; gap: 12px; align-items: end; }.filter-form :deep(.el-form-item) { margin: 0; }.filter-form :deep(.el-input), .filter-form :deep(.el-select) { width: 100%; }
.type-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 18px 0; }
.type-card { display: grid; gap: 8px; min-height: 102px; padding: 16px; border: 1px solid #dcdfe6; border-radius: 10px; background: #fff; color: #303133; text-align: left; cursor: pointer; }
.type-card span { color: #909399; line-height: 1.5; }.type-card.active { border-color: #409eff; background: #ecf5ff; }.type-card.disabled { cursor: not-allowed; opacity: .55; }
.create-project-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px 24px; }.create-project-form :deep(.el-form-item) { display: block; margin: 0; }.create-project-form :deep(.el-date-editor), .create-project-form :deep(.el-upload) { width: 100%; }.full { grid-column: 1 / -1; }.upload-control { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }.selected-file { display: flex; align-items: center; gap: 8px; min-width: 0; color: #606266; }.selected-file span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.el-pagination { justify-content: end; margin-top: 16px; }
@media (max-width: 767px) { .filter-form, .type-grid, .create-project-form { grid-template-columns: 1fr; }.full { grid-column: auto; } }
</style>
