<script setup lang="ts">
import { Plus, Refresh, Search } from "@element-plus/icons-vue"
import { onMounted, reactive, ref } from "vue"
import { ElMessage } from "element-plus"

import { supplierApi } from "../../api/supplier"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import {
  ARCHIVE_STATUS_LABELS,
  COOPERATION_STATUS_LABELS,
  type ArchiveStatus,
  type CooperationStatus,
  type SupplierListItem,
} from "../../types/supplier"

const auth = useAuthStore()
const loading = ref(false)
const suppliers = ref<SupplierListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
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
      <RouterLink v-if="auth.hasPermission('supplier:create')" to="/suppliers/new">
        <el-button type="primary" :icon="Plus">新增供应商</el-button>
      </RouterLink>
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
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }"><RouterLink :to="`/suppliers/${row.id}`"><el-button link type="primary">详情</el-button></RouterLink></template>
        </el-table-column>
      </el-table>
      <div class="pagination"><el-pagination background layout="total, prev, pager, next" :current-page="page" :page-size="pageSize" :total="total" @current-change="loadSuppliers" /></div>
    </el-card>
  </div>
</template>

<style scoped>
.supplier-page { display: grid; gap: 18px; }
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 24px 28px; border: 1px solid #dce9fa; border-radius: 14px; background: linear-gradient(115deg, #fff, #edf5ff); }
.page-heading p { margin: 0 0 6px; color: var(--brand-600); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.page-heading h1 { margin: 0 0 8px; color: #172b4d; font-size: 26px; }
.page-heading span { color: var(--text-secondary); font-size: 14px; }
.filter-card :deep(.el-card__body) { padding-bottom: 4px; }
.filter-action { align-self: end; }
.table-card strong { color: #344054; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
@media (max-width: 640px) { .page-heading { flex-direction: column; } }
</style>
