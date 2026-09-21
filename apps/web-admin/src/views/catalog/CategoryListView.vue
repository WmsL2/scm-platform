<script setup lang="ts">
import { onMounted, reactive, ref } from "vue"
import { Delete, Download, Edit, Plus, Refresh, Search, Upload } from "@element-plus/icons-vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { categoryApi } from "../../api/category"
import { useExcelImportNavigationLock } from "../../shared/import/excelImportNavigationLock"
import { useAuthStore } from "../../stores/auth"
import {
  deductionRateToPurchaseCoefficient,
  purchaseCoefficientToDeductionPercent,
  purchaseCoefficientToDeductionRate,
} from "./categoryDeduction"
import type { Category, CategoryImportResult, CategoryListParams, CategoryPayload } from "../../types/category"

const auth = useAuthStore()
const pageSize = 20
const rows = ref<Category[]>([])
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const importNavigationLock = useExcelImportNavigationLock()
const importVisible = ref(false)
const formVisible = ref(false)
const editingId = ref<string | null>(null)
const importFile = ref<File>()
const importCoefficient = ref("0.95")
const purchaseCoefficient = ref("0.95")
const importResult = ref<CategoryImportResult>()
const filters = reactive<{
  level1_name: string
  level2_name: string
  level3_name: string
  purchase_coefficient: string
  is_active: boolean | undefined
  business_unit: string
}>({ level1_name: "", level2_name: "", level3_name: "", purchase_coefficient: "", is_active: undefined, business_unit: "" })

function emptyPayload(): CategoryPayload {
  return {
    source_type: "MALL_LEVEL3",
    level1_external_id: null,
    level1_name: "",
    level2_external_id: null,
    level2_name: "",
    level3_external_id: null,
    level3_name: "",
    deduction_rate: "0.05",
    is_active: true,
    shelf_flag: null,
    business_unit: null,
  }
}

const form = reactive<CategoryPayload>(emptyPayload())

function categoryListParams(targetPage: number): CategoryListParams | null {
  const coefficient = filters.purchase_coefficient.trim()
  let deductionRate: string | undefined
  if (coefficient) {
    const converted = purchaseCoefficientToDeductionRate(coefficient)
    if (converted === null) {
      ElMessage.error("请输入 0 到 1 之间的采购价系数，最多 4 位小数，例如 0.95。")
      return null
    }
    deductionRate = converted
  }
  return {
    page: targetPage,
    page_size: pageSize,
    level1_name: filters.level1_name.trim() || undefined,
    level2_name: filters.level2_name.trim() || undefined,
    level3_name: filters.level3_name.trim() || undefined,
    deduction_rate: deductionRate,
    is_active: filters.is_active,
    business_unit: filters.business_unit.trim() || undefined,
  }
}

async function loadCategories(targetPage = page.value) {
  const params = categoryListParams(targetPage)
  if (!params) return
  loading.value = true
  try {
    const data = await categoryApi.list(params)
    rows.value = data.items
    total.value = data.total
    page.value = data.page
  } catch {
    ElMessage.error("加载类目列表失败")
  } finally {
    loading.value = false
  }
}

function search() { void loadCategories(1) }

function reset() {
  filters.level1_name = ""
  filters.level2_name = ""
  filters.level3_name = ""
  filters.purchase_coefficient = ""
  filters.is_active = undefined
  filters.business_unit = ""
  void loadCategories(1)
}

function openCreate() {
  editingId.value = null
  Object.assign(form, emptyPayload())
  purchaseCoefficient.value = "0.95"
  formVisible.value = true
}

function openEdit(category: Category) {
  editingId.value = category.id
  const { id: _id, ...payload } = category
  Object.assign(form, payload)
  purchaseCoefficient.value = deductionRateToPurchaseCoefficient(category.deduction_rate) ?? ""
  formVisible.value = true
}

async function saveCategory() {
  const deductionRate = purchaseCoefficientToDeductionRate(purchaseCoefficient.value)
  if (deductionRate === null) {
    ElMessage.error("请输入 0 到 1 之间的采购价系数，最多 4 位小数，例如 0.95。")
    return
  }
  saving.value = true
  try {
    const payload = { ...form, deduction_rate: deductionRate }
    if (editingId.value) {
      await categoryApi.update(editingId.value, payload)
      ElMessage.success("类目已更新")
    } else {
      await categoryApi.create(payload)
      page.value = 1
      ElMessage.success("类目已新增")
    }
    formVisible.value = false
    await loadCategories()
  } catch {
    ElMessage.error(editingId.value ? "更新类目失败" : "新增类目失败")
  } finally {
    saving.value = false
  }
}

async function deleteCategory(category: Category) {
  try {
    await ElMessageBox.confirm(
      `删除“${category.level3_name}”后不可恢复；如已被商品引用，系统会拒绝删除。`,
      "确认删除类目",
      { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" },
    )
    await categoryApi.remove(category.id)
    if (rows.value.length === 1 && page.value > 1) page.value -= 1
    ElMessage.success("类目已删除")
    await loadCategories()
  } catch (error) {
    if (error !== "cancel" && error !== "close") ElMessage.error("删除类目失败，可能仍被商品引用")
  }
}

async function downloadTemplate() {
  try {
    const blob = await categoryApi.template()
    const link = document.createElement("a")
    link.href = URL.createObjectURL(blob)
    link.download = "商城类目导入模板.xlsx"
    link.click()
    URL.revokeObjectURL(link.href)
  } catch {
    ElMessage.error("下载模板失败")
  }
}

function selectImportFile(event: Event) {
  importFile.value = (event.target as HTMLInputElement).files?.[0]
}

function resetImport() {
  importFile.value = undefined
  importCoefficient.value = "0.95"
  importResult.value = undefined
}

async function submitImport() {
  const deductionRatePercent = purchaseCoefficientToDeductionPercent(importCoefficient.value)
  if (!importFile.value) {
    ElMessage.error("请选择 Excel 文件")
    return
  }
  if (deductionRatePercent === null) {
    ElMessage.error("请输入 0 到 1 之间的采购价系数，最多 4 位小数，例如 0.95。")
    return
  }

  importing.value = true
  importNavigationLock.start()
  try {
    importResult.value = await categoryApi.import(importFile.value, deductionRatePercent)
    if (importResult.value.failed === 0) {
      page.value = 1
      await loadCategories()
      ElMessage.success(`导入完成：成功 ${importResult.value.success} 条，跳过 ${importResult.value.skipped} 条`)
    }
  } catch {
    ElMessage.error("导入失败，请检查文件和采购价系数")
  } finally {
    importNavigationLock.stop()
    importing.value = false
  }
}

onMounted(loadCategories)
</script>

<template>
  <section class="category-page">
    <header class="page-heading">
      <div>
        <p>CATEGORY MASTER</p>
        <h1>类目管理</h1>
        <span>维护商城三级类目、启用状态及采购价系数规则。</span>
      </div>
      <div class="header-actions">
        <el-button v-if="auth.hasPermission('product:import')" @click="downloadTemplate"><el-icon><Download /></el-icon>下载模板</el-button>
        <el-button v-if="auth.hasPermission('product:import')" @click="importVisible = true"><el-icon><Upload /></el-icon>导入 Excel</el-button>
        <el-button v-if="auth.hasPermission('category:create')" type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新增类目</el-button>
      </div>
    </header>

    <el-card class="page-card filter-card">
      <el-form :inline="true" label-position="top" @submit.prevent="search">
        <el-form-item label="一级类目" class="filter-item filter-item-category"><el-input v-model="filters.level1_name" clearable placeholder="请输入一级类目" @keyup.enter="search" /></el-form-item>
        <el-form-item label="二级类目" class="filter-item filter-item-category"><el-input v-model="filters.level2_name" clearable placeholder="请输入二级类目" @keyup.enter="search" /></el-form-item>
        <el-form-item label="三级类目" class="filter-item filter-item-category"><el-input v-model="filters.level3_name" clearable placeholder="请输入三级类目" @keyup.enter="search" /></el-form-item>
        <el-form-item label="采购价系数" class="filter-item filter-item-coefficient"><el-input v-model="filters.purchase_coefficient" clearable placeholder="0.95" @keyup.enter="search"><template #prepend>×</template></el-input></el-form-item>
        <el-form-item label="状态" class="filter-item filter-item-status"><el-select v-model="filters.is_active" clearable placeholder="全部"><el-option label="启用" :value="true" /><el-option label="停用" :value="false" /></el-select></el-form-item>
        <el-form-item label="主营事业部" class="filter-item filter-item-business"><el-input v-model="filters.business_unit" clearable placeholder="请输入主营事业部" @keyup.enter="search" /></el-form-item>
        <el-form-item class="filter-actions"><el-button type="primary" :icon="Search" :loading="loading" @click="search">查询</el-button><el-button :icon="Refresh" @click="reset">重置</el-button></el-form-item>
      </el-form>
    </el-card>

    <el-card class="page-card table-card">
      <template #header><strong>类目列表</strong></template>
      <el-table v-loading="loading" :data="rows" empty-text="暂无类目数据">
        <el-table-column prop="level1_name" label="一级类目" min-width="130" />
        <el-table-column prop="level2_name" label="二级类目" min-width="130" />
        <el-table-column prop="level3_name" label="三级类目" min-width="150" />
        <el-table-column label="采购价系数" width="130"><template #default="{ row }">×{{ deductionRateToPurchaseCoefficient(row.deduction_rate) ?? "-" }}</template></el-table-column>
        <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag effect="plain" :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "停用" }}</el-tag></template></el-table-column>
        <el-table-column prop="business_unit" label="主营事业部" min-width="130" />
        <el-table-column v-if="auth.hasPermission('category:update') || auth.hasPermission('category:delete')" label="操作" fixed="right" width="145">
          <template #default="{ row }">
            <el-button v-if="auth.hasPermission('category:update')" link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
            <el-button v-if="auth.hasPermission('category:delete')" link type="danger" :icon="Delete" @click="deleteCategory(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination"><el-pagination background layout="total, prev, pager, next" :current-page="page" :page-size="pageSize" :total="total" @current-change="(value: number) => { page = value; loadCategories() }" /></div>
    </el-card>

    <el-dialog v-model="formVisible" :title="editingId ? '编辑类目' : '新增类目'" width="680px">
      <el-form label-position="top" class="category-form">
        <el-form-item label="类目来源"><el-select v-model="form.source_type"><el-option label="商城三级类目" value="MALL_LEVEL3" /><el-option label="工业产品线" value="INDUSTRIAL_LINE" /></el-select></el-form-item>
        <el-form-item label="一级类目 ID"><el-input v-model="form.level1_external_id" /></el-form-item>
        <el-form-item label="一级类目名称" required><el-input v-model="form.level1_name" /></el-form-item>
        <el-form-item label="二级类目 ID"><el-input v-model="form.level2_external_id" /></el-form-item>
        <el-form-item label="二级类目名称" required><el-input v-model="form.level2_name" /></el-form-item>
        <el-form-item label="三级类目 ID"><el-input v-model="form.level3_external_id" /></el-form-item>
        <el-form-item label="三级类目名称" required><el-input v-model="form.level3_name" /></el-form-item>
        <el-form-item label="采购价系数" required><el-input v-model="purchaseCoefficient" placeholder="0.95"><template #prepend>×</template></el-input><el-text class="coefficient-help" type="info">示例：0.95 表示扣点 5%，即协议价采购价 = 协议价 × 0.95。</el-text></el-form-item>
        <el-form-item label="有效状态"><el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" /></el-form-item>
        <el-form-item label="上下柜标记"><el-input v-model="form.shelf_flag" /></el-form-item>
        <el-form-item label="主营事业部"><el-input v-model="form.business_unit" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="formVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="saveCategory">保存</el-button></template>
    </el-dialog>

    <el-dialog v-model="importVisible" title="商城类目 Excel 导入" width="560px" @closed="resetImport">
      <el-form label-position="top">
        <el-form-item label="选择 Excel" required>
          <el-button @click="$refs.importInput?.click()">选择 Excel</el-button>
          <input ref="importInput" type="file" accept=".xlsx" hidden @change="selectImportFile" />
          <span v-if="importFile" class="selected-file">已选择：{{ importFile.name }}</span>
        </el-form-item>
        <el-form-item label="本批次采购价系数" required>
          <el-input v-model="importCoefficient" placeholder="0.95"><template #prepend>×</template></el-input>
          <el-text class="coefficient-help" type="info">示例：填写 0.95，表示扣点 5%；协议价 100 元时，协议价采购价 = 100 × 0.95 = 95 元。</el-text>
        </el-form-item>
        <p class="import-tip">本次 Excel 中所有新导入类目统一使用该采购价系数。Excel 颜色不参与扣点规则判断。</p>
      </el-form>
      <el-alert v-if="importResult" :type="importResult.failed ? 'error' : 'success'" :title="`总计 ${importResult.total}，成功 ${importResult.success}，跳过 ${importResult.skipped}，失败 ${importResult.failed}`" :closable="false" />
      <el-table v-if="importResult?.errors.length" :data="importResult.errors" max-height="220">
        <el-table-column prop="row_number" label="行号" width="70" /><el-table-column prop="field" label="字段" /><el-table-column prop="value" label="值" /><el-table-column prop="reason" label="原因" min-width="160" />
      </el-table>
      <template #footer><el-button @click="importVisible = false">取消</el-button><el-button type="primary" :loading="importing" @click="submitImport">导入</el-button></template>
    </el-dialog>
  </section>
</template>

<style scoped>
.category-page { display: grid; gap: 18px; }
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 24px 28px; border: 1px solid #dce9fa; border-radius: 14px; background: linear-gradient(115deg, #fff, #edf5ff); }
.header-actions { display: flex; gap: 8px; }
.page-heading p { margin: 0 0 6px; color: var(--brand-600); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.page-heading h1 { margin: 0 0 8px; color: #172b4d; font-size: 26px; }
.page-heading span, .import-tip { color: var(--text-secondary); }
.filter-card :deep(.el-card__body) { padding-bottom: 4px; }
.filter-item-category { width: 240px; }
.filter-item-coefficient { width: 296px; }
.filter-item-status { width: 160px; }
.filter-item-business { width: 240px; }
.filter-item :deep(.el-input), .filter-item :deep(.el-select) { width: 100%; }
.filter-actions { width: 190px; align-self: end; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.category-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 16px; }
.selected-file { margin-left: 12px; color: var(--text-secondary); }
.coefficient-help { display: block; margin-top: 6px; line-height: 1.5; }
@media (max-width: 900px) { .filter-item-category, .filter-item-coefficient, .filter-item-status, .filter-item-business { width: min(100%, 280px); } }
@media (max-width: 640px) { .page-heading { flex-direction: column; } .category-form { grid-template-columns: 1fr; } .filter-actions { width: 190px; } }
</style>
