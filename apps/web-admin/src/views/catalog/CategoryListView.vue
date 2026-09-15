<script setup lang="ts">
import { onMounted, reactive, ref } from "vue"
import { Delete, Download, Edit, Plus, Upload } from "@element-plus/icons-vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { categoryApi } from "../../api/category"
import { ratioToPercent } from "./categoryDeduction"
import type { Category, CategoryImportResult, CategoryPayload } from "../../types/category"

const pageSize = 20
const rows = ref<Category[]>([])
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const saving = ref(false)
const importing = ref(false)
const importVisible = ref(false)
const formVisible = ref(false)
const editingId = ref<string | null>(null)
const importFile = ref<File>()
const importRatio = ref("0.08")
const importResult = ref<CategoryImportResult>()

function emptyPayload(): CategoryPayload {
  return {
    source_type: "MALL_LEVEL3",
    level1_external_id: null,
    level1_name: "",
    level2_external_id: null,
    level2_name: "",
    level3_external_id: null,
    level3_name: "",
    deduction_rate: "0.0800",
    is_active: true,
    shelf_flag: null,
    business_unit: null,
  }
}

const form = reactive<CategoryPayload>(emptyPayload())

async function loadCategories() {
  loading.value = true
  try {
    const data = await categoryApi.list(page.value, pageSize)
    rows.value = data.items
    total.value = data.total
  } catch {
    ElMessage.error("加载类目列表失败")
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, emptyPayload())
  formVisible.value = true
}

function openEdit(category: Category) {
  editingId.value = category.id
  const { id: _id, ...payload } = category
  Object.assign(form, payload)
  formVisible.value = true
}

async function saveCategory() {
  saving.value = true
  try {
    if (editingId.value) {
      await categoryApi.update(editingId.value, { ...form })
      ElMessage.success("类目已更新")
    } else {
      await categoryApi.create({ ...form })
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
  importRatio.value = "0.08"
  importResult.value = undefined
}

async function submitImport() {
  const deductionRatePercent = ratioToPercent(importRatio.value)
  if (!importFile.value) {
    ElMessage.error("请选择 Excel 文件")
    return
  }
  if (deductionRatePercent === null) {
    ElMessage.error("请输入 0 到 1 之间、最多四位小数的扣点倍率，例如 0.08")
    return
  }

  importing.value = true
  try {
    importResult.value = await categoryApi.import(importFile.value, deductionRatePercent)
    if (importResult.value.failed === 0) {
      page.value = 1
      await loadCategories()
      ElMessage.success(`导入完成：成功 ${importResult.value.success} 条，跳过 ${importResult.value.skipped} 条`)
    }
  } catch {
    ElMessage.error("导入失败，请检查文件和扣点率")
  } finally {
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
        <span>维护商城三级类目、启用状态及扣点规则。</span>
      </div>
      <div class="header-actions">
        <el-button @click="downloadTemplate"><el-icon><Download /></el-icon>下载模板</el-button>
        <el-button @click="importVisible = true"><el-icon><Upload /></el-icon>导入 Excel</el-button>
        <el-button type="primary" @click="openCreate"><el-icon><Plus /></el-icon>新增类目</el-button>
      </div>
    </header>

    <el-card class="page-card table-card">
      <template #header><strong>类目列表</strong></template>
      <el-table v-loading="loading" :data="rows" empty-text="暂无类目数据">
        <el-table-column prop="level1_name" label="一级类目" min-width="130" />
        <el-table-column prop="level2_name" label="二级类目" min-width="130" />
        <el-table-column prop="level3_name" label="三级类目" min-width="150" />
        <el-table-column label="扣点率" width="110"><template #default="{ row }">×{{ row.deduction_rate }}</template></el-table-column>
        <el-table-column label="状态" width="100"><template #default="{ row }"><el-tag effect="plain" :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "停用" }}</el-tag></template></el-table-column>
        <el-table-column prop="business_unit" label="主营事业部" min-width="130" />
        <el-table-column label="操作" fixed="right" width="145">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" @click="deleteCategory(row)">删除</el-button>
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
        <el-form-item label="扣点倍率" required><el-input v-model="form.deduction_rate"><template #prepend>×</template></el-input></el-form-item>
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
        <el-form-item label="本批次扣点率" required>
          <el-input v-model="importRatio" placeholder="0.08"><template #prepend>×</template></el-input>
        </el-form-item>
        <p class="import-tip">本次 Excel 中所有新导入类目统一使用该扣点率。Excel 颜色不参与扣点率判断。</p>
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
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.category-form { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 16px; }
.selected-file { margin-left: 12px; color: var(--text-secondary); }
@media (max-width: 640px) { .page-heading { flex-direction: column; } .category-form { grid-template-columns: 1fr; } }
</style>
