<script setup lang="ts">
import { EditPen, Refresh, Search, Upload } from "@element-plus/icons-vue"
import { onMounted, reactive, ref } from "vue"
import { ElMessage } from "element-plus"
import { useRoute, useRouter } from "vue-router"

import { productApi } from "../../api/catalog"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type {
  ProductImportPreview,
  ProductImportSupplierCandidate,
  ProductListItem,
} from "../../types/catalog"

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const products = ref<ProductListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const filters = reactive({
  keyword: "",
  source_supplier_id: typeof route.query.source_supplier_id === "string" ? route.query.source_supplier_id : "",
})
const importInput = ref<HTMLInputElement>()
const importing = ref(false)
const importDialogVisible = ref(false)
const importPreview = ref<ProductImportPreview>()
const supplierCandidates = ref<ProductImportSupplierCandidate[]>([])
const selections = reactive<Record<string, string>>({})

async function loadProducts(targetPage = page.value): Promise<void> {
  loading.value = true
  try {
    const result = await productApi.list({
      keyword: filters.keyword,
      source_supplier_id: filters.source_supplier_id || undefined,
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
  filters.source_supplier_id = ""
  void router.replace({ name: "product-list" })
  void loadProducts(1)
}

function money(value: string | null): string {
  return value === null ? "—" : `¥ ${value}`
}

function productImageUrl(reference: string | null): string | undefined {
  if (!reference) return undefined
  if (/^https?:\/\//i.test(reference)) return reference
  const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "")
  return `${baseUrl}/${reference.replace(/^\//, "")}`
}

function openImport(): void {
  importInput.value?.click()
}

async function previewImport(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const [file] = Array.from(input.files ?? [])
  input.value = ""
  if (!file) return
  importing.value = true
  try {
    importPreview.value = await productApi.previewImport(file)
    if (auth.hasPermission("product:import:resolve")) {
      supplierCandidates.value = await productApi.importSupplierCandidates()
    }
    importDialogVisible.value = true
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "商品 Excel 预览失败")
  } finally {
    importing.value = false
  }
}

async function resolveSupplier(matchId: string): Promise<void> {
  if (!importPreview.value || !selections[matchId]) return
  importing.value = true
  try {
    importPreview.value = await productApi.resolveImportSupplier(
      importPreview.value.id,
      matchId,
      selections[matchId],
    )
    ElMessage.success("来源供应商已解析，已重新校验该批次")
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "来源供应商解析失败")
  } finally {
    importing.value = false
  }
}

async function confirmImport(): Promise<void> {
  if (!importPreview.value) return
  importing.value = true
  try {
    const result = await productApi.confirmImport(importPreview.value.id)
    ElMessage.success(`已正式导入 ${result.imported_count} 条商品`)
    importDialogVisible.value = false
    importPreview.value = undefined
    await loadProducts(1)
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "确认导入失败")
  } finally {
    importing.value = false
  }
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
      <div class="header-actions">
        <el-button
          v-if="auth.hasPermission('product:import')"
          type="primary"
          :icon="Upload"
          :loading="importing"
          @click="openImport"
        >
          导入 Excel
        </el-button>
        <input ref="importInput" class="file-input" type="file" accept=".xlsx" @change="previewImport" />
      </div>
    </header>

    <el-card class="page-card filter-card">
      <el-alert
        v-if="filters.source_supplier_id"
        title="正在查看当前供应商的相关商品"
        description="此列表仅显示商品来源供应商为当前供应商的正式商品。"
        type="info"
        :closable="false"
        show-icon
        class="supplier-filter-notice"
      />
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
          <el-button :icon="Refresh" @click="reset">{{ filters.source_supplier_id ? "查看全部商品" : "重置" }}</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="page-card table-card">
      <template #header><strong>商品列表</strong></template>
      <el-table v-loading="loading" :data="products" empty-text="暂无正式商品数据">
        <el-table-column label="商品图片" width="108" fixed="left">
          <template #default="{ row }">
            <el-image
              v-if="productImageUrl(row.image_reference)"
              class="product-thumbnail"
              :src="productImageUrl(row.image_reference)"
              fit="contain"
              :preview-src-list="[productImageUrl(row.image_reference)]"
              preview-teleported
            >
              <template #error><div class="image-placeholder">加载失败</div></template>
            </el-image>
            <div v-else class="image-placeholder">暂无图片</div>
          </template>
        </el-table-column>
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

    <el-dialog
      v-model="importDialogVisible"
      title="商品主数据 Excel 导入预览"
      width="min(1120px, 96vw)"
      :close-on-click-modal="false"
    >
      <template v-if="importPreview">
        <el-alert :type="importPreview.status === 'READY_TO_CONFIRM' ? 'success' : 'warning'" :closable="false" show-icon>
          共 {{ importPreview.total_rows }} 行；通过 {{ importPreview.valid_rows }} 行；待处理 {{ importPreview.invalid_rows }} 行。
          只有全部校验通过后才会写入正式商品库。
        </el-alert>

        <h3>来源供应商解析</h3>
        <el-table :data="importPreview.supplier_matches" max-height="240">
          <el-table-column prop="supplier_name_normalized" label="Excel 供应商名称" min-width="220" />
          <el-table-column label="状态" width="130">
            <template #default="{ row }"><el-tag :type="row.match_status === 'MATCHED' ? 'success' : 'warning'">{{ row.match_status }}</el-tag></template>
          </el-table-column>
          <el-table-column label="系统供应商" min-width="220">
            <template #default="{ row }">{{ row.matched_supplier_name ? `${row.matched_supplier_code} / ${row.matched_supplier_name}` : '未解析' }}</template>
          </el-table-column>
          <el-table-column v-if="auth.hasPermission('product:import:resolve')" label="人工解析" min-width="300">
            <template #default="{ row }">
              <template v-if="row.match_status !== 'MATCHED'">
                <el-select v-model="selections[row.id]" filterable placeholder="选择已归档且正常的供应商" style="width: 220px">
                  <el-option v-for="supplier in supplierCandidates" :key="supplier.id" :label="`${supplier.supplier_code} / ${supplier.supplier_name}`" :value="supplier.id" />
                </el-select>
                <el-button link type="primary" :disabled="!selections[row.id] || importing" @click="resolveSupplier(row.id)">确认解析</el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>

        <h3>行校验结果</h3>
        <el-table :data="importPreview.rows" max-height="300">
          <el-table-column prop="source_row_number" label="Excel 行" width="90" />
          <el-table-column prop="product_name" label="商品名称" min-width="180" show-overflow-tooltip />
          <el-table-column label="图片" width="85">
            <template #default="{ row }">{{ row.image_saved ? "已保存" : "—" }}</template>
          </el-table-column>
          <el-table-column prop="category_path" label="类目" min-width="220" show-overflow-tooltip />
          <el-table-column prop="supplier_name_raw" label="供应商原值" min-width="180" />
          <el-table-column label="结果" min-width="260">
            <template #default="{ row }">
              <el-tag :type="row.is_valid ? 'success' : 'danger'">{{ row.is_valid ? '通过' : row.error_message }}</el-tag>
              <small v-if="row.warning_message" class="import-warning">{{ row.warning_message }}</small>
            </template>
          </el-table-column>
        </el-table>
      </template>
      <template #footer>
        <el-button :disabled="importing" @click="importDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="importing" :disabled="importPreview?.status !== 'READY_TO_CONFIRM'" @click="confirmImport">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.product-page { display: grid; gap: 18px; }
.page-heading { display: flex; justify-content: space-between; gap: 16px; padding: 24px 28px; border: 1px solid #dce9fa; border-radius: 14px; background: linear-gradient(115deg, #fff, #edf5ff); }
.page-heading p { margin: 0 0 6px; color: var(--brand-600); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.page-heading h1 { margin: 0 0 8px; color: #172b4d; font-size: 26px; }
.page-heading span { color: var(--text-secondary); font-size: 14px; }
.filter-card :deep(.el-card__body) { padding-bottom: 4px; }
.supplier-filter-notice { margin-bottom: 16px; }
.filter-action { align-self: end; }
.table-card strong { color: #344054; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.header-actions { display: flex; align-items: flex-start; }
.file-input { display: none; }
.import-warning { display: block; margin-top: 5px; color: var(--text-secondary); }
.product-thumbnail, .image-placeholder { width: 68px; height: 68px; border: 1px solid var(--border); border-radius: 6px; }
.image-placeholder { display: grid; place-items: center; padding: 6px; box-sizing: border-box; color: var(--text-secondary); background: #f8fafc; font-size: 12px; text-align: center; }
</style>
