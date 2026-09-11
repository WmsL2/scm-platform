<script setup lang="ts">
import { Delete, Download, Plus, Refresh, Search, Upload } from "@element-plus/icons-vue"
import { onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"

import { supplierApi } from "../../api/supplier"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import {
  ARCHIVE_STATUS_LABELS,
  COOPERATION_STATUS_LABELS,
  type ArchiveStatus,
  type CooperationStatus,
  type SupplierImportPreview,
  type SupplierListItem,
} from "../../types/supplier"

const auth = useAuthStore()
const loading = ref(false)
const suppliers = ref<SupplierListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const importInput = ref<HTMLInputElement>()
const importPreview = ref<SupplierImportPreview | null>(null)
const importDialogVisible = ref(false)
const importing = ref(false)
const importArchiveStatus = ref<ArchiveStatus>("ARCHIVED")
const filters = reactive<{
  keyword: string
  archive_status: ArchiveStatus | undefined
  cooperation_status: CooperationStatus | undefined
}>({ keyword: "", archive_status: undefined, cooperation_status: undefined })

async function loadSuppliers(targetPage = page.value): Promise<void> {
  loading.value = true
  try {
    const result = await supplierApi.list({ ...filters, page: targetPage, page_size: pageSize })
    suppliers.value = result.items
    total.value = result.total
    page.value = result.page
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载供应商列表失败")
  } finally {
    loading.value = false
  }
}

function search(): void {
  void loadSuppliers(1)
}

function reset(): void {
  filters.keyword = ""
  filters.archive_status = undefined
  filters.cooperation_status = undefined
  void loadSuppliers(1)
}

function archiveLabel(status: ArchiveStatus): string {
  return ARCHIVE_STATUS_LABELS[status]
}

function cooperationLabel(status: CooperationStatus): string {
  return COOPERATION_STATUS_LABELS[status]
}

async function deleteSupplier(supplier: SupplierListItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `删除后“${supplier.supplier_name}”不会出现在正常列表中，但数据库会保留审计和历史数据。`,
      "确认逻辑删除",
      { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" },
    )
    await supplierApi.delete(supplier.id)
    ElMessage.success("供应商已标记为已删除")
    await loadSuppliers(suppliers.value.length === 1 && page.value > 1 ? page.value - 1 : page.value)
  } catch (error) {
    if (error === "cancel" || error === "close") return
    ElMessage.error(error instanceof HttpError ? error.response.message : "删除供应商失败")
  }
}

async function downloadTemplate(): Promise<void> {
  try {
    const blob = await supplierApi.downloadImportTemplate()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = "supplier-import-template.xlsx"
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "下载导入模板失败")
  }
}

function openImportDialog(): void {
  importArchiveStatus.value = "ARCHIVED"
  importInput.value?.click()
}

async function previewImport(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const [file] = Array.from(input.files ?? [])
  input.value = ""
  if (!file) return
  importing.value = true
  try {
    importPreview.value = await supplierApi.previewImport(file)
    importDialogVisible.value = true
    if (importPreview.value.invalid_rows) {
      ElMessage.warning(`发现 ${importPreview.value.invalid_rows} 行错误，请修正 Excel 后重新上传`)
      return
    }
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "Excel 导入预览失败")
  } finally {
    importing.value = false
  }
}

async function confirmImport(): Promise<void> {
  if (!importPreview.value || importPreview.value.invalid_rows) return
  importing.value = true
  try {
    const result = await supplierApi.confirmImport(importPreview.value.id, importArchiveStatus.value)
    ElMessage.success(`成功导入 ${result.imported_count} 家供应商`)
    importDialogVisible.value = false
    importPreview.value = null
    await loadSuppliers(1)
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "确认导入失败")
  } finally {
    importing.value = false
  }
}

onMounted(() => void loadSuppliers())
</script>

<template>
  <div class="supplier-page">
    <header class="page-heading">
      <div>
        <p>SUPPLIER MASTER</p>
        <h1>供应商管理</h1>
        <span>维护供应商基础资料与归档、合作状态。</span>
      </div>
      <div class="header-actions">
        <el-button v-if="auth.hasPermission('supplier:create')" :icon="Download" @click="downloadTemplate">下载模板</el-button>
        <el-button v-if="auth.hasPermission('supplier:create')" :icon="Upload" :loading="importing" @click="openImportDialog">导入 Excel</el-button>
        <input ref="importInput" class="file-input" type="file" accept=".xlsx" @change="previewImport" />
        <RouterLink v-if="auth.hasPermission('supplier:create')" to="/suppliers/new">
          <el-button type="primary" :icon="Plus">新增供应商</el-button>
        </RouterLink>
      </div>
    </header>

    <el-card class="page-card filter-card">
      <el-form :inline="true" label-position="top" @submit.prevent="search">
        <el-form-item label="关键字">
          <el-input v-model="filters.keyword" clearable placeholder="编码、名称或主营品牌" @keyup.enter="search" />
        </el-form-item>
        <el-form-item label="归档状态">
          <el-select v-model="filters.archive_status" clearable placeholder="全部">
            <el-option v-for="(label, value) in ARCHIVE_STATUS_LABELS" :key="value" :label="label" :value="value" />
          </el-select>
        </el-form-item>
        <el-form-item label="合作状态">
          <el-select v-model="filters.cooperation_status" clearable placeholder="全部">
            <el-option v-for="(label, value) in COOPERATION_STATUS_LABELS" :key="value" :label="label" :value="value" />
          </el-select>
        </el-form-item>
        <el-form-item class="filter-action">
          <el-button type="primary" :icon="Search" :loading="loading" @click="search">查询</el-button>
          <el-button :icon="Refresh" @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="page-card table-card">
      <template #header><strong>供应商列表</strong></template>
      <el-table v-loading="loading" :data="suppliers" empty-text="暂无供应商数据">
        <el-table-column prop="supplier_code" label="供应商编码" min-width="150" />
        <el-table-column prop="supplier_name" label="供应商名称" min-width="180" />
        <el-table-column prop="main_brands" label="主营品牌" min-width="150" />
        <el-table-column prop="advantage" label="主要优势" min-width="180" show-overflow-tooltip />
        <el-table-column label="归档状态" min-width="120">
          <template #default="{ row }"><el-tag effect="plain">{{ archiveLabel(row.archive_status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="合作状态" min-width="120">
          <template #default="{ row }"><el-tag :type="row.cooperation_status === 'NORMAL' ? 'success' : row.cooperation_status === 'STOPPED' ? 'warning' : 'danger'" effect="plain">{{ cooperationLabel(row.cooperation_status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <RouterLink :to="`/suppliers/${row.id}`"><el-button link type="primary">详情</el-button></RouterLink>
            <el-button v-if="auth.hasPermission('supplier:delete')" link type="danger" :icon="Delete" @click="deleteSupplier(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination"><el-pagination background layout="total, prev, pager, next" :current-page="page" :page-size="pageSize" :total="total" @current-change="loadSuppliers" /></div>
    </el-card>

    <el-dialog v-model="importDialogVisible" title="供应商 Excel 导入预览" width="min(940px, 94vw)" :close-on-click-modal="false">
      <template v-if="importPreview">
        <el-alert :type="importPreview.invalid_rows ? 'warning' : 'success'" :closable="false" show-icon>
          共 {{ importPreview.total_rows }} 行；有效 {{ importPreview.valid_rows }} 行；错误 {{ importPreview.invalid_rows }} 行。
          有错误时请修正 Excel 后重新上传；无错误时请先选择本批供应商的初始归档状态，再确认导入。合作状态固定为“正常合作”。
        </el-alert>
        <el-form v-if="!importPreview.invalid_rows" label-position="top" class="import-status-form">
          <el-form-item label="本批初始归档状态">
            <el-select v-model="importArchiveStatus" placeholder="请选择归档状态">
              <el-option v-for="(label, value) in ARCHIVE_STATUS_LABELS" :key="value" :label="label" :value="value" />
            </el-select>
          </el-form-item>
        </el-form>
        <el-table :data="importPreview.rows" max-height="380" class="import-preview-table">
          <el-table-column prop="source_row_number" label="Excel 行" width="90" />
          <el-table-column prop="supplier_name" label="供应商名称" min-width="160" />
          <el-table-column prop="main_brands" label="主营品牌" min-width="150" />
          <el-table-column prop="advantage" label="主要优势" min-width="160" show-overflow-tooltip />
          <el-table-column prop="contact_name" label="联系人" min-width="120" />
          <el-table-column prop="contact_phone" label="联系电话" min-width="140" />
          <el-table-column label="校验结果" min-width="180">
            <template #default="{ row }"><el-tag :type="row.is_valid ? 'success' : 'danger'">{{ row.is_valid ? '通过' : row.error_message }}</el-tag></template>
          </el-table-column>
        </el-table>
      </template>
      <template #footer>
        <el-button @click="importDialogVisible = false">关闭</el-button>
        <el-button v-if="importPreview && !importPreview.invalid_rows" type="primary" :loading="importing" @click="confirmImport">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.supplier-page { display: grid; gap: 18px; }
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 24px 28px; border: 1px solid #dce9fa; border-radius: 14px; background: linear-gradient(115deg, #fff, #edf5ff); }
.header-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
.file-input { display: none; }
.page-heading p { margin: 0 0 6px; color: var(--brand-600); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.page-heading h1 { margin: 0 0 8px; color: #172b4d; font-size: 26px; }
.page-heading span { color: var(--text-secondary); font-size: 14px; }
.filter-card :deep(.el-card__body) { padding-bottom: 4px; }
.filter-action { align-self: end; }
.table-card strong { color: #344054; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.import-preview-table { margin-top: 16px; }
.import-status-form { margin-top: 16px; }
@media (max-width: 640px) { .page-heading { flex-direction: column; } }
</style>
