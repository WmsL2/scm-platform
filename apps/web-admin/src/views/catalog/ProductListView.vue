<script setup lang="ts">
import { Delete, Download, EditPen, Refresh, Search, Setting, Upload } from "@element-plus/icons-vue"
import { computed, onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useRoute, useRouter } from "vue-router"

import { productApi } from "../../api/catalog"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import {
  derivedLevel1Keys,
  derivedLevel2Keys,
  updateExplicitSelection,
  visibleSelection,
} from "./categoryMultiSelect"
import type {
  ProductImportPreview,
  ProductImportSupplierCandidate,
  ProductCategoryFilterOption,
  ProductListItem,
} from "../../types/catalog"

type CategorySelectInstance = {
  scrollbarRef?: {
    wrapRef?: HTMLElement
  }
}

type CategoryPopupPosition = { scrollTop: number; scrollLeft: number }

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const products = ref<ProductListItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const advancedVisible = ref(false)
const directCategoryLevel1Names = ref<string[]>([])
const directCategoryLevel2Keys = ref<string[]>([])
const directCategoryLevel3Ids = ref<string[]>([])
const categoryOptionsByKey = ref(new Map<string, ProductCategoryFilterOption>())
const categoryOptionResults = reactive<Record<ProductCategoryFilterOption["level"], ProductCategoryFilterOption[]>>({
  LEVEL1: [], LEVEL2: [], LEVEL3: [],
})
const categoryOptionLoading = reactive<Record<ProductCategoryFilterOption["level"], boolean>>({
  LEVEL1: false, LEVEL2: false, LEVEL3: false,
})
const categoryOptionNextOffset = reactive<Record<ProductCategoryFilterOption["level"], number>>({
  LEVEL1: 0, LEVEL2: 0, LEVEL3: 0,
})
const categoryOptionHasMore = reactive<Record<ProductCategoryFilterOption["level"], boolean>>({
  LEVEL1: true, LEVEL2: true, LEVEL3: true,
})
const categoryOptionKeyword = reactive<Record<ProductCategoryFilterOption["level"], string>>({
  LEVEL1: "", LEVEL2: "", LEVEL3: "",
})
const categoryLevel1SelectRef = ref<CategorySelectInstance>()
const categoryLevel2SelectRef = ref<CategorySelectInstance>()
const categoryLevel3SelectRef = ref<CategorySelectInstance>()
const categorySearchSequence = { LEVEL1: 0, LEVEL2: 0, LEVEL3: 0 }
const filters = reactive({
  keyword: "",
  source_supplier_id: typeof route.query.source_supplier_id === "string" ? route.query.source_supplier_id : "",
  company_name: "",
  purchasing_agent: "",
  brand: "",
  supplier_name: "",
  cost_price_min: "",
  cost_price_max: "",
  agreement_price_min: "",
  agreement_price_max: "",
  discount_rate_min: "",
  discount_rate_max: "",
  sales_volume_min: "",
  sales_volume_max: "",
  status: "ACTIVE" as "ACTIVE" | "DISABLED",
})
const columnStorageKey = "scm.product-list.visible-columns.v1"
const defaultColumns = ["image", "sku", "product_name", "brand", "company_name", "purchasing_agent", "category", "supplier", "cost_price", "agreement_price", "discount_rate", "sales_volume", "status", "updated_at"]
const columnOptions = [
  ["image", "商品图片"], ["sku", "SKU"], ["product_name", "商品名称"], ["brand", "品牌"],
  ["company_name", "所属公司"], ["purchasing_agent", "采销员"], ["model", "型号"], ["category", "三级类目"],
  ["supplier", "供应商"], ["cost_price", "成本价"], ["market_price", "市场价"], ["jd_price", "京东价"],
  ["agreement_price", "协议价"], ["discount_rate", "折扣率"], ["sales_volume", "销量"], ["positive_rating", "好评率"],
  ["status", "状态"], ["updated_at", "最后更新时间"],
] as const
const storedColumns = localStorage.getItem(columnStorageKey)
const visibleColumns = ref<string[]>(storedColumns ? JSON.parse(storedColumns) : defaultColumns)
const level1Options = computed(() => optionsFor("LEVEL1", selectedCategoryLevel1Names.value))
const level2Options = computed(() => optionsFor("LEVEL2", selectedCategoryLevel2Keys.value))
const level3Options = computed(() => optionsFor("LEVEL3", directCategoryLevel3Ids.value))
const derivedCategoryLevel2Keys = computed(() => derivedLevel2Keys(
  categoryOptionsByKey.value,
  directCategoryLevel3Ids.value,
))
const derivedCategoryLevel1Names = computed(() => derivedLevel1Keys(
  categoryOptionsByKey.value,
  directCategoryLevel2Keys.value,
  directCategoryLevel3Ids.value,
))
const selectedCategoryLevel1Names = computed(() => visibleSelection(
  directCategoryLevel1Names.value,
  derivedCategoryLevel1Names.value,
))
const selectedCategoryLevel2Keys = computed(() => visibleSelection(
  directCategoryLevel2Keys.value,
  derivedCategoryLevel2Keys.value,
))
const categorySelections = computed(() => [
  ...directCategoryLevel1Names.value,
  ...directCategoryLevel2Keys.value,
  ...directCategoryLevel3Ids.value,
])
const importInput = ref<HTMLInputElement>()
const importing = ref(false)
const importDialogVisible = ref(false)
const importPreview = ref<ProductImportPreview>()
const supplierCandidates = ref<ProductImportSupplierCandidate[]>([])
const selections = reactive<Record<string, string>>({})
const importRowFilter = ref<"ALL" | "PASSED" | "FAILED" | "UPDATE">("ALL")
const importRowsLoading = ref(false)
const activeTab = ref<"products" | "audit">("products")

async function loadProducts(targetPage = page.value): Promise<void> {
  loading.value = true
  try {
    const result = await productApi.list({
      keyword: filters.keyword,
      company_name: filters.company_name,
      purchasing_agent: filters.purchasing_agent,
      brand: filters.brand,
      supplier_name: filters.supplier_name,
      category_selections: categorySelections.value,
      source_supplier_id: filters.source_supplier_id || undefined,
      cost_price_min: filters.cost_price_min,
      cost_price_max: filters.cost_price_max,
      agreement_price_min: filters.agreement_price_min,
      agreement_price_max: filters.agreement_price_max,
      discount_rate_min: percentQuery(filters.discount_rate_min),
      discount_rate_max: percentQuery(filters.discount_rate_max),
      sales_volume_min: filters.sales_volume_min,
      sales_volume_max: filters.sales_volume_max,
      status: filters.status,
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
  Object.assign(filters, {
    keyword: "", source_supplier_id: "", company_name: "", purchasing_agent: "", brand: "",
    supplier_name: "", cost_price_min: "", cost_price_max: "", agreement_price_min: "",
    agreement_price_max: "", discount_rate_min: "", discount_rate_max: "", sales_volume_min: "",
    sales_volume_max: "", status: "ACTIVE",
  })
  clearCategoryFilters()
  void router.replace({ name: "product-list" })
  void loadProducts(1)
}

function clearCategoryFilters(): void {
  directCategoryLevel1Names.value = []
  directCategoryLevel2Keys.value = []
  directCategoryLevel3Ids.value = []
}

function updateCategoryLevel1(nextValues: string[]): void {
  directCategoryLevel1Names.value = updateExplicitSelection(
    directCategoryLevel1Names.value,
    selectedCategoryLevel1Names.value,
    nextValues,
    derivedCategoryLevel1Names.value,
  )
}

function updateCategoryLevel2(nextValues: string[]): void {
  directCategoryLevel2Keys.value = updateExplicitSelection(
    directCategoryLevel2Keys.value,
    selectedCategoryLevel2Keys.value,
    nextValues,
    derivedCategoryLevel2Keys.value,
  )
}

function optionsFor(
  level: ProductCategoryFilterOption["level"], selectedKeys: string[],
): ProductCategoryFilterOption[] {
  const options = new Map(categoryOptionResults[level].map((item) => [item.selection_key, item]))
  for (const key of selectedKeys) {
    const option = categoryOptionsByKey.value.get(key)
    if (option) options.set(key, option)
  }
  return Array.from(options.values())
}

async function searchCategoryOptions(
  level: ProductCategoryFilterOption["level"], keyword = "",
): Promise<void> {
  const sequence = ++categorySearchSequence[level]
  const normalizedKeyword = keyword.trim()
  categoryOptionKeyword[level] = normalizedKeyword
  categoryOptionNextOffset[level] = 0
  categoryOptionHasMore[level] = true
  await loadCategoryOptions(level, sequence, false)
}

async function loadNextCategoryOptions(
  level: ProductCategoryFilterOption["level"],
): Promise<void> {
  if (categoryOptionLoading[level] || !categoryOptionHasMore[level]) return
  await loadCategoryOptions(level, categorySearchSequence[level], true)
}

async function loadCategoryOptions(
  level: ProductCategoryFilterOption["level"], sequence: number, append: boolean,
): Promise<void> {
  categoryOptionLoading[level] = true
  try {
    const offset = append ? categoryOptionNextOffset[level] : 0
    const result = await productApi.categoryFilterOptions(
      level,
      categoryOptionKeyword[level],
      offset,
      categorySelections.value,
      filters.status,
    )
    if (sequence !== categorySearchSequence[level]) return
    categoryOptionResults[level] = append
      ? mergeCategoryOptions(categoryOptionResults[level], result.items)
      : result.items
    categoryOptionNextOffset[level] = offset + result.items.length
    categoryOptionHasMore[level] = result.has_more
    const cache = new Map<string, ProductCategoryFilterOption>(categoryOptionsByKey.value)
    for (const option of result.items) {
      cache.set(option.selection_key, option)
      cache.set(option.level1_selection_key, {
        ...option, selection_key: option.level1_selection_key, label: option.level1_label, level: "LEVEL1",
      })
      cache.set(option.level2_selection_key, {
        ...option, selection_key: option.level2_selection_key, label: option.level2_label, level: "LEVEL2",
      })
    }
    categoryOptionsByKey.value = cache
  } catch (error) {
    if (sequence === categorySearchSequence[level]) {
      ElMessage.error(error instanceof HttpError ? error.response.message : "加载类目选项失败")
    }
  } finally {
    if (sequence === categorySearchSequence[level]) categoryOptionLoading[level] = false
  }
}

function mergeCategoryOptions(
  existing: ProductCategoryFilterOption[], incoming: ProductCategoryFilterOption[],
): ProductCategoryFilterOption[] {
  const options = new Map(existing.map((item) => [item.selection_key, item]))
  for (const item of incoming) options.set(item.selection_key, item)
  return Array.from(options.values())
}

function onCategoryEndReached(
  level: ProductCategoryFilterOption["level"], direction: "top" | "bottom" | "left" | "right",
): void {
  if (direction !== "bottom") return
  void loadNextCategoryOptions(level)
}

function categorySelectScrollWrap(level: ProductCategoryFilterOption["level"]): HTMLElement | undefined {
  const select = level === "LEVEL1"
    ? categoryLevel1SelectRef.value
    : level === "LEVEL2"
      ? categoryLevel2SelectRef.value
      : categoryLevel3SelectRef.value
  return select?.scrollbarRef?.wrapRef
}

function onCategoryPopupScroll(
  level: ProductCategoryFilterOption["level"], position: CategoryPopupPosition,
): void {
  const wrap = categorySelectScrollWrap(level)
  // Element Plus may not emit end-reached until the scrollbar reaches its exact last pixel.
  // Start the next request slightly earlier, while keeping the loading/has-more guards in one place.
  if (!wrap || position.scrollTop + wrap.clientHeight < wrap.scrollHeight - 24) return
  void loadNextCategoryOptions(level)
}

function percentQuery(value: string): string | undefined {
  if (!value.trim()) return undefined
  const parsed = Number(value)
  return Number.isFinite(parsed) ? String(parsed / 100) : value
}

function percent(value: string | null): string {
  return value === null ? "—" : `${(Number(value) * 100).toFixed(2).replace(/\.00$/, "")}%`
}

function isVisible(key: string): boolean { return visibleColumns.value.includes(key) }
function saveVisibleColumns(): void { localStorage.setItem(columnStorageKey, JSON.stringify(visibleColumns.value)) }

function money(value: string | null): string {
  return value === null ? "—" : `¥ ${value}`
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false })
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

async function downloadImportTemplate(): Promise<void> {
  importing.value = true
  try {
    const blob = await productApi.downloadImportTemplate()
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "商品大表模板.xlsx"
    link.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "下载模板失败")
  } finally {
    importing.value = false
  }
}

async function previewImport(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const [file] = Array.from(input.files ?? [])
  input.value = ""
  if (!file) return
  importing.value = true
  try {
    importPreview.value = await productApi.previewImport(file)
    importRowFilter.value = "ALL"
    if (auth.hasPermission("product:import:resolve")) {
      supplierCandidates.value = await productApi.importSupplierCandidates()
    }
    importDialogVisible.value = true
  } catch (error) {
    ElMessage.error(
      error instanceof HttpError
        ? error.response.message
        : "商品 Excel 上传或预览超时，请检查网络和服务状态后重试",
    )
  } finally {
    importing.value = false
  }
}

async function loadImportRows(targetPage = 1): Promise<void> {
  if (!importPreview.value) return
  importRowsLoading.value = true
  try {
    importPreview.value = await productApi.getImportPreview(importPreview.value.id, {
      page: targetPage,
      page_size: 50,
      row_status: importRowFilter.value,
    })
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载导入明细失败")
  } finally {
    importRowsLoading.value = false
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
    importRowFilter.value = "ALL"
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
    await loadImportRows(1)
    ElMessage.success(`本次新增 ${result.created_count} 条，更新 ${result.updated_count} 条商品`)
    if (result.status === "CONFIRMED") {
      importDialogVisible.value = false
      importPreview.value = undefined
    }
    await loadProducts(1)
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "确认导入失败")
  } finally {
    importing.value = false
  }
}

async function disableProduct(product: ProductListItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `停用后“${product.product_name ?? product.sku ?? "该商品"}”将不能查询、编辑或通过 Excel 重复导入；商品记录和 SKU 仍会保留。`,
      "确认停用商品",
      { confirmButtonText: "停用", cancelButtonText: "取消", type: "warning" },
    )
    await productApi.disable(product.id)
    ElMessage.success("商品已停用")
    await loadProducts(products.value.length === 1 && page.value > 1 ? page.value - 1 : page.value)
  } catch (error) {
    if (error === "cancel" || error === "close") return
    ElMessage.error(error instanceof HttpError ? error.response.message : "停用商品失败")
  }
}

async function enableProduct(product: ProductListItem): Promise<void> {
  try {
    await productApi.enable(product.id)
    ElMessage.success("商品已启用")
    await loadProducts()
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "启用商品失败")
  }
}

async function purgeProduct(product: ProductListItem): Promise<void> {
  const verification = product.sku ?? product.product_name ?? ""
  try {
    const { value } = await ElMessageBox.prompt(
      `永久删除后无法恢复，重新导入同一供应商和 SKU 会创建一条新商品。请输入“${verification}”确认。`,
      "永久删除商品",
      { confirmButtonText: "永久删除", cancelButtonText: "取消", inputPlaceholder: verification, type: "error" },
    )
    if (value !== verification) {
      ElMessage.error("确认内容不匹配，未执行永久删除")
      return
    }
    await productApi.purge(product.id)
    ElMessage.success("商品已永久删除")
    await loadProducts(products.value.length === 1 && page.value > 1 ? page.value - 1 : page.value)
  } catch (error) {
    if (error === "cancel" || error === "close") return
    ElMessage.error(error instanceof HttpError ? error.response.message : "永久删除商品失败")
  }
}

onMounted(() => { void loadProducts() })
</script>

<template>
  <div class="product-page">
    <header class="page-heading">
      <div>
        <p>PRODUCT MASTER</p>
        <h1>商品主数据</h1>
        <span>查询正式商品；停用商品保留 SKU 防重键，永久删除后才能重新导入同键商品。</span>
      </div>
      <div class="header-actions">
        <el-button
          v-if="auth.hasPermission('product:import')"
          :icon="Download"
          :loading="importing"
          @click="downloadImportTemplate"
        >
          下载模板
        </el-button>
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

    <el-tabs v-model="activeTab" class="product-tabs">
      <el-tab-pane label="商品列表" name="products" />
      <el-tab-pane label="操作记录" name="audit" />
    </el-tabs>

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
        <el-form-item label="自定义搜索">
          <el-input
            v-model="filters.keyword"
            clearable
            placeholder="相机、数码、品牌、SKU、类目等"
            style="width: 240px"
            @keyup.enter="loadProducts(1)"
          />
        </el-form-item>
        <el-form-item v-if="auth.hasPermission('product:disable')" label="商品状态">
          <el-select v-model="filters.status" style="width: 140px">
            <el-option label="正常" value="ACTIVE" />
            <el-option label="已停用" value="DISABLED" />
          </el-select>
        </el-form-item>
        <el-form-item class="filter-action">
          <el-button type="primary" :icon="Search" :loading="loading" @click="loadProducts(1)">
            查询
          </el-button>
          <el-button :icon="Refresh" @click="reset">{{ filters.source_supplier_id ? "查看全部商品" : "重置" }}</el-button>
          <el-button @click="advancedVisible = !advancedVisible">{{ advancedVisible ? "收起" : "更多筛选" }}</el-button>
        </el-form-item>
        <div v-show="advancedVisible" class="advanced-filters">
          <el-form-item label="所属公司"><el-input v-model="filters.company_name" clearable placeholder="输入所属公司" /></el-form-item>
          <el-form-item label="采销员"><el-input v-model="filters.purchasing_agent" clearable placeholder="输入采销员" /></el-form-item>
          <el-form-item label="品牌"><el-input v-model="filters.brand" clearable placeholder="输入品牌" /></el-form-item>
          <el-form-item label="供应商"><el-input v-model="filters.supplier_name" clearable placeholder="输入供应商名称" /></el-form-item>
          <el-form-item label="一级类目">
            <el-select ref="categoryLevel1SelectRef" :model-value="selectedCategoryLevel1Names" multiple filterable remote reserve-keyword clearable collapse-tags collapse-tags-tooltip :loading="categoryOptionLoading.LEVEL1" placeholder="搜索一级类目" style="width: 240px" :remote-method="(keyword: string) => searchCategoryOptions('LEVEL1', keyword)" @focus="searchCategoryOptions('LEVEL1')" @popup-scroll="(position: CategoryPopupPosition) => onCategoryPopupScroll('LEVEL1', position)" @end-reached="(direction: 'top' | 'bottom' | 'left' | 'right') => onCategoryEndReached('LEVEL1', direction)" @update:model-value="updateCategoryLevel1">
              <el-option v-for="item in level1Options" :key="item.selection_key" :label="item.label" :value="item.selection_key" />
            </el-select>
          </el-form-item>
          <el-form-item label="二级类目">
            <el-select ref="categoryLevel2SelectRef" :model-value="selectedCategoryLevel2Keys" multiple filterable remote reserve-keyword clearable collapse-tags collapse-tags-tooltip :loading="categoryOptionLoading.LEVEL2" placeholder="直接搜索二级类目" style="width: 240px" :remote-method="(keyword: string) => searchCategoryOptions('LEVEL2', keyword)" @focus="searchCategoryOptions('LEVEL2')" @popup-scroll="(position: CategoryPopupPosition) => onCategoryPopupScroll('LEVEL2', position)" @end-reached="(direction: 'top' | 'bottom' | 'left' | 'right') => onCategoryEndReached('LEVEL2', direction)" @update:model-value="updateCategoryLevel2">
              <el-option v-for="item in level2Options" :key="item.selection_key" :label="item.label" :value="item.selection_key" />
            </el-select>
          </el-form-item>
          <el-form-item label="三级类目">
            <el-select ref="categoryLevel3SelectRef" v-model="directCategoryLevel3Ids" multiple filterable remote reserve-keyword clearable collapse-tags collapse-tags-tooltip :loading="categoryOptionLoading.LEVEL3" placeholder="直接搜索三级类目" style="width: 280px" :remote-method="(keyword: string) => searchCategoryOptions('LEVEL3', keyword)" @focus="searchCategoryOptions('LEVEL3')" @popup-scroll="(position: CategoryPopupPosition) => onCategoryPopupScroll('LEVEL3', position)" @end-reached="(direction: 'top' | 'bottom' | 'left' | 'right') => onCategoryEndReached('LEVEL3', direction)">
              <el-option v-for="item in level3Options" :key="item.selection_key" :label="item.label" :value="item.selection_key" />
            </el-select>
          </el-form-item>
          <el-form-item label="成本价区间"><div class="range-input"><el-input v-model="filters.cost_price_min" inputmode="decimal" placeholder="大于等于" /><span>—</span><el-input v-model="filters.cost_price_max" inputmode="decimal" placeholder="小于等于" /></div></el-form-item>
          <el-form-item label="协议价区间"><div class="range-input"><el-input v-model="filters.agreement_price_min" inputmode="decimal" placeholder="大于等于" /><span>—</span><el-input v-model="filters.agreement_price_max" inputmode="decimal" placeholder="小于等于" /></div></el-form-item>
          <el-form-item label="折扣率区间（%）"><div class="range-input"><el-input v-model="filters.discount_rate_min" inputmode="decimal" placeholder="例如 80" /><span>—</span><el-input v-model="filters.discount_rate_max" inputmode="decimal" placeholder="例如 95" /></div></el-form-item>
          <el-form-item label="销量区间"><div class="range-input"><el-input v-model="filters.sales_volume_min" inputmode="numeric" placeholder="大于等于" /><span>—</span><el-input v-model="filters.sales_volume_max" inputmode="numeric" placeholder="小于等于" /></div></el-form-item>
        </div>
      </el-form>
    </el-card>

    <el-card class="page-card table-card">
      <template #header>
        <div class="table-heading">
          <strong>{{ activeTab === "products" ? "商品列表" : "商品操作记录" }}</strong>
          <el-popover v-if="activeTab === 'products'" placement="bottom-end" :width="260" trigger="click">
            <template #reference><el-button :icon="Setting">自定义显示列</el-button></template>
            <el-checkbox-group v-model="visibleColumns" class="column-picker" @change="saveVisibleColumns">
              <el-checkbox v-for="option in columnOptions" :key="option[0]" :label="option[0]">{{ option[1] }}</el-checkbox>
            </el-checkbox-group>
          </el-popover>
        </div>
      </template>
      <el-table v-if="activeTab === 'products'" v-loading="loading" :data="products" empty-text="暂无正式商品数据">
        <el-table-column v-if="isVisible('image')" label="商品图片" width="108" fixed="left">
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
        <el-table-column v-if="isVisible('sku')" prop="sku" label="SKU" min-width="130" />
        <el-table-column v-if="isVisible('product_name')" prop="product_name" label="商品名称" min-width="200" show-overflow-tooltip />
        <el-table-column v-if="isVisible('brand')" prop="brand" label="品牌" min-width="120" />
        <el-table-column v-if="isVisible('company_name')" prop="company_name" label="所属公司" min-width="150" />
        <el-table-column v-if="isVisible('purchasing_agent')" prop="purchasing_agent" label="采销员" min-width="120" />
        <el-table-column v-if="isVisible('model')" prop="model" label="型号" min-width="150" />
        <el-table-column v-if="isVisible('category')" prop="category_path" label="三级类目" min-width="220" show-overflow-tooltip />
        <el-table-column v-if="isVisible('supplier')" prop="source_supplier_name" label="供应商" min-width="160" />
        <el-table-column v-if="isVisible('cost_price')" label="成本价" min-width="125">
          <template #default="{ row }">{{ money(row.cost_price) }}</template>
        </el-table-column>
        <el-table-column v-if="isVisible('market_price')" label="市场价" min-width="125"><template #default="{ row }">{{ money(row.market_price) }}</template></el-table-column>
        <el-table-column v-if="isVisible('jd_price')" label="京东价" min-width="125"><template #default="{ row }">{{ money(row.jd_price) }}</template></el-table-column>
        <el-table-column v-if="isVisible('agreement_price')" label="协议价" min-width="125">
          <template #default="{ row }">{{ money(row.agreement_price) }}</template>
        </el-table-column>
        <el-table-column v-if="isVisible('discount_rate')" label="折扣率" min-width="105"><template #default="{ row }">{{ percent(row.discount_rate) }}</template></el-table-column>
        <el-table-column v-if="isVisible('sales_volume')" prop="sales_volume" label="销量" min-width="100" />
        <el-table-column v-if="isVisible('positive_rating')" label="好评率" min-width="105"><template #default="{ row }">{{ percent(row.positive_rating) }}</template></el-table-column>
        <el-table-column v-if="isVisible('status')" label="状态" width="100">
          <template #default="{ row }"><el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'">{{ row.status === 'ACTIVE' ? '正常' : '已停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column v-if="isVisible('updated_at')" label="最后更新时间" min-width="180"><template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template></el-table-column>
        <el-table-column label="操作" width="270" fixed="right">
          <template #default="{ row }">
            <RouterLink v-if="row.status === 'ACTIVE'" :to="`/products/${row.id}`"><el-button link type="primary">详情</el-button></RouterLink>
            <RouterLink
              v-if="row.status === 'ACTIVE' && auth.hasPermission('product:cost:update')"
              :to="`/products/${row.id}?editCost=1`"
            >
              <el-button link type="warning" :icon="EditPen">更新成本</el-button>
            </RouterLink>
            <el-button v-if="row.status === 'ACTIVE' && auth.hasPermission('product:disable')" link type="warning" @click="disableProduct(row)">停用</el-button>
            <el-button v-if="row.status === 'DISABLED' && auth.hasPermission('product:disable')" link type="success" @click="enableProduct(row)">启用</el-button>
            <el-button v-if="row.status === 'DISABLED' && auth.hasPermission('product:purge')" link type="danger" :icon="Delete" @click="purgeProduct(row)">永久删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-table v-else v-loading="loading" :data="products" empty-text="暂无正式商品数据">
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
        <el-table-column prop="product_name" label="商品名称" min-width="220" show-overflow-tooltip />
        <el-table-column prop="brand" label="品牌" min-width="120" />
        <el-table-column prop="model" label="型号" min-width="150" />
        <el-table-column prop="sku" label="SKU" min-width="150" />
        <el-table-column label="导入人" min-width="130">
          <template #default="{ row }">{{ row.created_by_username ?? "—" }}</template>
        </el-table-column>
        <el-table-column label="导入时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="最后更新人" min-width="130">
          <template #default="{ row }">{{ row.updated_by_username ?? "—" }}</template>
        </el-table-column>
        <el-table-column label="最后更新时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
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
        <el-alert :type="importPreview.valid_rows > 0 ? 'success' : 'warning'" :closable="false" show-icon>
          共 {{ importPreview.total_rows }} 行；已处理 {{ importPreview.imported_rows }} 行；通过 {{ importPreview.valid_rows }} 行；更新 {{ importPreview.update_rows }} 行；不通过 {{ importPreview.invalid_rows }} 行。
          “通过”行会新增商品，“更新”行会覆盖同键正常商品的模板字段；不通过行保留在当前预览中，不会入库。
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
        <el-radio-group v-model="importRowFilter" class="import-row-filter" @change="loadImportRows(1)">
          <el-radio-button label="ALL">全部（{{ importPreview.total_rows }}）</el-radio-button>
          <el-radio-button label="PASSED">通过（{{ importPreview.valid_rows }}）</el-radio-button>
          <el-radio-button label="UPDATE">更新（{{ importPreview.update_rows }}）</el-radio-button>
          <el-radio-button label="FAILED">不通过（{{ importPreview.invalid_rows }}）</el-radio-button>
        </el-radio-group>
        <el-table v-loading="importRowsLoading" :data="importPreview.rows" max-height="300">
          <el-table-column prop="source_row_number" label="Excel 行" width="90" />
          <el-table-column prop="product_name" label="商品名称" min-width="180" show-overflow-tooltip />
          <el-table-column label="图片" width="85">
            <template #default="{ row }">{{ row.image_saved ? "已保存" : row.image_pending_save ? "确认后保存" : "—" }}</template>
          </el-table-column>
          <el-table-column prop="category_path" label="类目" min-width="220" show-overflow-tooltip />
          <el-table-column prop="supplier_name_raw" label="供应商原值" min-width="180" />
          <el-table-column label="状态" width="105">
            <template #default="{ row }">
              <el-tag v-if="row.is_imported" type="info">{{ row.write_action === "UPDATE" ? "已更新" : "已导入" }}</el-tag>
              <el-tag v-else-if="row.write_action === 'UPDATE'" type="warning">更新</el-tag>
              <el-tag v-else :type="row.is_valid ? 'success' : 'danger'">{{ row.is_valid ? '通过' : '不通过' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="结果" min-width="260">
            <template #default="{ row }">
              <span v-if="row.is_imported">{{ row.write_action === "UPDATE" ? "已更新正式商品库" : "已写入正式商品库" }}</span>
              <span v-else-if="row.write_action === 'UPDATE'">将更新正式商品：{{ row.changed_fields?.length ? row.changed_fields.join("、") : "无业务字段变化" }}</span>
              <span v-else-if="!row.is_valid" class="import-error">{{ row.error_message }}</span>
              <span v-else>校验通过</span>
              <small v-if="row.warning_message" class="import-warning">{{ row.warning_message }}</small>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-if="importPreview.row_total > importPreview.page_size"
          class="pagination"
          layout="prev, pager, next, total"
          :current-page="importPreview.page"
          :page-size="importPreview.page_size"
          :total="importPreview.row_total"
          @current-change="loadImportRows"
        />
      </template>
      <template #footer>
        <el-button :disabled="importing" @click="importDialogVisible = false">关闭</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importPreview || importPreview.valid_rows + importPreview.update_rows === 0" @click="confirmImport">
          确认新增/更新 {{ (importPreview?.valid_rows ?? 0) + (importPreview?.update_rows ?? 0) }} 行
        </el-button>
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
.advanced-filters { display: flex; flex-wrap: wrap; gap: 0 12px; width: 100%; padding-top: 8px; border-top: 1px solid var(--border); }
.range-input { display: flex; align-items: center; gap: 8px; width: 310px; }
.table-heading { display: flex; align-items: center; justify-content: space-between; }
.column-picker { display: grid; grid-template-columns: 1fr 1fr; }
.table-card strong { color: #344054; }
.pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
.header-actions { display: flex; align-items: flex-start; }
.product-tabs { margin-bottom: -4px; }
.file-input { display: none; }
.import-warning { display: block; margin-top: 5px; color: var(--text-secondary); }
.import-error { color: var(--el-color-danger); }
.import-row-filter { margin: -4px 0 12px; }
.product-thumbnail, .image-placeholder { width: 68px; height: 68px; border: 1px solid var(--border); border-radius: 6px; }
.image-placeholder { display: grid; place-items: center; padding: 6px; box-sizing: border-box; color: var(--text-secondary); background: #f8fafc; font-size: 12px; text-align: center; }
</style>
