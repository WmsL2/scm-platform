<script setup lang="ts">
import { EditPen, Refresh, Search } from "@element-plus/icons-vue"
import { onMounted, reactive, ref } from "vue"
import { ElMessage } from "element-plus"

import { productApi } from "../../api/catalog"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type { ProductListItem } from "../../types/catalog"

const auth = useAuthStore()
const loading = ref(false)
const products = ref<ProductListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const filters = reactive({ keyword: "" })

async function loadProducts(targetPage = page.value): Promise<void> {
  loading.value = true
  try {
    const result = await productApi.list({
      keyword: filters.keyword,
      page: targetPage,
      page_size: pageSize,
    })
    products.value = result.items
    total.value = result.total
    page.value = result.page
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载商品列表失败")
  } finally {
    loading.value = false
  }
}

function reset(): void {
  filters.keyword = ""
  void loadProducts(1)
}

function money(value: string | null): string {
  return value === null ? "—" : `¥ ${value}`
}

onMounted(() => void loadProducts())
</script>

<template>
  <div class="product-page">
    <header class="page-heading">
      <div>
        <p>PRODUCT MASTER</p>
        <h1>商品主数据</h1>
        <span>查询正式商品；当前成本价更新会同步重算已冻结的定价字段。</span>
      </div>
    </header>

    <el-card class="page-card filter-card">
      <el-form :inline="true" label-position="top" @submit.prevent="loadProducts(1)">
        <el-form-item label="关键字">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="品牌、型号、SKU、名称、货号或69码"
            @keyup.enter="loadProducts(1)"
          />
        </el-form-item>
        <el-form-item class="filter-action">
          <el-button type="primary" :icon="Search" :loading="loading" @click="loadProducts(1)">
            查询
          </el-button>
          <el-button :icon="Refresh" @click="reset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="page-card table-card">
      <template #header><strong>商品列表</strong></template>
      <el-table v-loading="loading" :data="products" empty-text="暂无正式商品数据">
        <el-table-column prop="product_name" label="商品名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="brand" label="品牌" min-width="120" />
        <el-table-column prop="model" label="型号" min-width="150" />
        <el-table-column prop="sku" label="SKU" min-width="130" />
        <el-table-column prop="category_path" label="三级类目" min-width="220" show-overflow-tooltip />
        <el-table-column label="当前成本价" min-width="125">
          <template #default="{ row }">{{ money(row.cost_price) }}</template>
        </el-table-column>
        <el-table-column label="协议价" min-width="125">
          <template #default="{ row }">{{ money(row.agreement_price) }}</template>
        </el-table-column>
        <el-table-column prop="source_supplier_name" label="来源供应商" min-width="160" />
        <el-table-column label="操作" width="155" fixed="right">
          <template #default="{ row }">
            <RouterLink :to="`/products/${row.id}`"><el-button link type="primary">详情</el-button></RouterLink>
            <RouterLink
              v-if="auth.hasPermission('product:cost:update')"
              :to="`/products/${row.id}?editCost=1`"
            >
              <el-button link type="warning" :icon="EditPen">更新成本</el-button>
            </RouterLink>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :current-page="page"
          :page-size="pageSize"
          :total="total"
          @current-change="loadProducts"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.product-page { display: grid; gap: 18px; }
.page-heading { padding: 24px 28px; border: 1px solid #dce9fa; border-radius: 14px; background: linear-gradient(115deg, #fff, #edf5ff); }
.page-heading p { margin: 0 0 6px; color: var(--brand-600); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.page-heading h1 { margin: 0 0 8px; color: #172b4d; font-size: 26px; }
.page-heading span { color: var(--text-secondary); font-size: 14px; }
.filter-card :deep(.el-card__body) { padding-bottom: 4px; }
.filter-action { align-self: end; }
.table-card strong { color: #344054; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
