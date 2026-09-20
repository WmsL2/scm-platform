<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { ElMessage } from "element-plus"

import { productApi } from "../../api/catalog"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type { ProductCategoryFilterOption, ProductDetail, ProductUpdatePayload } from "../../types/catalog"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const submitting = ref(false)
const product = ref<ProductDetail | null>(null)
const editCostVisible = ref(route.query.editCost === "1")
const editVisible = ref(false)
const categoryOptions = reactive<Record<ProductCategoryFilterOption["level"], ProductCategoryFilterOption[]>>({
  LEVEL1: [], LEVEL2: [], LEVEL3: [],
})
const categoryLevel1 = ref("")
const categoryLevel2 = ref("")
const categoryLevel3 = ref("")
const imageInput = ref<HTMLInputElement>()
const form = reactive({ cost_price: "" })
const editForm = reactive({
  company_name: "",
  listed_at: "",
  brand: "",
  model: "",
  product_name: "",
  item_number: "",
  jd_same_product_url: "",
  purchasing_agent: "",
  barcode_text: "",
  certification_3c_code: "",
  product_specification: "",
  selling_points: "",
  packaging_list: "",
  warranty_period: "",
  remark: "",
  restricted_regions: "",
  reference_url: "",
  storefront_type: "",
  cost_price: "",
  market_price: "",
  jd_price: "",
  agreement_price: "",
  agreement_purchase_price: "",
  profit: "",
  jd_margin: "",
  deduction_review: "",
  gross_margin: "",
  jd_self_operated_price: "",
  sales_volume: "",
  positive_rating: "",
  discount_rate: "",
  price_inflation_rate: "",
  tax_code: "",
  invoice_name: "",
  tax_category: "",
  shipping_courier: "",
  after_sales_policy: "",
})
const priceFields: { key: keyof typeof editForm; label: string }[] = [
  { key: "cost_price", label: "成本价" }, { key: "market_price", label: "市场价" },
  { key: "jd_price", label: "京东价" }, { key: "agreement_price", label: "协议价" },
  { key: "agreement_purchase_price", label: "协议采购价" }, { key: "profit", label: "利润" },
  { key: "jd_self_operated_price", label: "京东自营前台价" },
]
const rateFields: { key: keyof typeof editForm; label: string }[] = [
  { key: "jd_margin", label: "京东价毛利" }, { key: "deduction_review", label: "扣点复核" },
  { key: "gross_margin", label: "毛利率" }, { key: "positive_rating", label: "好评率" },
  { key: "discount_rate", label: "折扣率" }, { key: "price_inflation_rate", label: "价格虚高比例" },
]
const level1Options = computed(() => uniqueNames(categoryOptions.LEVEL1.map((item) => item.level1_label)))
const level2Options = computed(() => uniqueNames(categoryOptions.LEVEL2.map((item) => item.label.split(" / ").at(-1) ?? item.label)))
const level3Options = computed(() => uniqueNames(categoryOptions.LEVEL3.map((item) => item.label.split(" / ").at(-1) ?? item.label)))
const productId = computed(() => String(route.params.id))
const canUpdateCost = computed(
  () => auth.hasPermission("product:cost:update") && product.value,
)
const canUpdate = computed(() => auth.hasPermission("product:update"))
const imageUrl = computed(() => {
  const reference = product.value?.image_reference
  if (!reference) return undefined
  if (/^https?:\/\//i.test(reference)) return reference
  const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000").replace(/\/$/, "")
  return `${baseUrl}/${reference.replace(/^\//, "")}`
})

async function loadProduct(): Promise<void> {
  loading.value = true
  try {
    product.value = await productApi.get(productId.value)
    form.cost_price = product.value.cost_price ?? ""
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载商品详情失败")
  } finally {
    loading.value = false
  }
}

function money(value: string | null): string {
  return value === null ? "—" : `¥ ${value}`
}
function percent(value: string | null): string { return value === null ? "—" : `${(Number(value) * 100).toFixed(2).replace(/\.00$/, "")}%` }
function percentInput(value: string | null): string { return value === null ? "" : String(Number(value) * 100) }
function percentPayload(value: string): string | null { const parsed = nullable(value); return parsed === null ? null : String(Number(parsed) / 100) }

async function updateCost(): Promise<void> {
  submitting.value = true
  try {
    product.value = await productApi.updateCost(productId.value, form.cost_price)
    ElMessage.success("成本价已更新，其他价格保持不变")
    editCostVisible.value = false
    await router.replace({ query: {} })
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "更新成本价失败")
  } finally {
    submitting.value = false
  }
}

function populateEditForm(item: ProductDetail): void {
  editForm.company_name = item.company_name ?? ""
  editForm.listed_at = item.listed_at ?? ""
  editForm.brand = item.brand ?? ""
  editForm.model = item.model ?? ""
  editForm.product_name = item.product_name ?? ""
  editForm.item_number = item.item_number ?? ""
  editForm.jd_same_product_url = item.jd_same_product_url ?? ""
  editForm.purchasing_agent = item.purchasing_agent ?? ""
  editForm.barcode_text = item.barcode_text ?? ""
  editForm.certification_3c_code = item.certification_3c_code ?? ""
  editForm.product_specification = item.product_specification ?? ""
  editForm.selling_points = item.selling_points ?? ""
  editForm.packaging_list = item.packaging_list ?? ""
  editForm.warranty_period = item.warranty_period ?? ""
  editForm.remark = item.remark ?? ""
  editForm.restricted_regions = item.restricted_regions ?? ""
  editForm.reference_url = item.reference_url ?? ""
  editForm.storefront_type = item.storefront_type ?? ""
  editForm.cost_price = item.cost_price ?? ""
  editForm.market_price = item.market_price ?? ""
  editForm.jd_price = item.jd_price ?? ""
  editForm.agreement_price = item.agreement_price ?? ""
  editForm.agreement_purchase_price = item.agreement_purchase_price ?? ""
  editForm.profit = item.profit ?? ""
  editForm.jd_margin = percentInput(item.jd_margin)
  editForm.deduction_review = percentInput(item.deduction_review)
  editForm.gross_margin = percentInput(item.gross_margin)
  editForm.jd_self_operated_price = item.jd_self_operated_price ?? ""
  editForm.sales_volume = item.sales_volume === null ? "" : String(item.sales_volume)
  editForm.positive_rating = percentInput(item.positive_rating)
  editForm.discount_rate = percentInput(item.discount_rate)
  editForm.price_inflation_rate = percentInput(item.price_inflation_rate)
  editForm.tax_code = item.tax_code ?? ""
  editForm.invoice_name = item.invoice_name ?? ""
  editForm.tax_category = item.tax_category ?? ""
  editForm.shipping_courier = item.shipping_courier ?? ""
  editForm.after_sales_policy = item.after_sales_policy ?? ""
  categoryLevel1.value = item.category_level1_name ?? ""
  categoryLevel2.value = item.category_level2_name ?? ""
  categoryLevel3.value = item.category_level3_name ?? ""
}

function nullable(value: string): string | null {
  const normalized = value.trim()
  return normalized || null
}

async function openEdit(): Promise<void> {
  if (!product.value || submitting.value) return
  submitting.value = true
  try {
    populateEditForm(product.value)
    await loadCategoryOptions("LEVEL1", categoryLevel1.value)
    await loadCategoryOptions("LEVEL2", categoryLevel2.value)
    await loadCategoryOptions("LEVEL3", categoryLevel3.value)
    editVisible.value = true
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载类目候选失败")
  } finally {
    submitting.value = false
  }
}

async function updateProduct(): Promise<void> {
  if (!categoryLevel1.value.trim() || !categoryLevel2.value.trim() || !categoryLevel3.value.trim()) {
    ElMessage.warning("请填写三级类目")
    return
  }
  const payload: ProductUpdatePayload = {
    company_name: nullable(editForm.company_name),
    listed_at: nullable(editForm.listed_at),
    brand: nullable(editForm.brand),
    model: nullable(editForm.model),
    product_name: nullable(editForm.product_name),
    category_level1_name: categoryLevel1.value.trim(),
    category_level2_name: categoryLevel2.value.trim(),
    category_level3_name: categoryLevel3.value.trim(),
    item_number: nullable(editForm.item_number),
    jd_same_product_url: nullable(editForm.jd_same_product_url),
    cost_price: nullable(editForm.cost_price),
    market_price: nullable(editForm.market_price),
    jd_price: nullable(editForm.jd_price),
    agreement_price: nullable(editForm.agreement_price),
    agreement_purchase_price: nullable(editForm.agreement_purchase_price),
    profit: nullable(editForm.profit),
    jd_margin: percentPayload(editForm.jd_margin),
    deduction_review: percentPayload(editForm.deduction_review),
    gross_margin: percentPayload(editForm.gross_margin),
    purchasing_agent: nullable(editForm.purchasing_agent),
    barcode_text: nullable(editForm.barcode_text),
    certification_3c_code: nullable(editForm.certification_3c_code),
    product_specification: nullable(editForm.product_specification),
    selling_points: nullable(editForm.selling_points),
    packaging_list: nullable(editForm.packaging_list),
    warranty_period: nullable(editForm.warranty_period),
    remark: nullable(editForm.remark),
    restricted_regions: nullable(editForm.restricted_regions),
    reference_url: nullable(editForm.reference_url),
    storefront_type: nullable(editForm.storefront_type),
    sales_volume: editForm.sales_volume.trim() ? Number(editForm.sales_volume) : null,
    positive_rating: percentPayload(editForm.positive_rating),
    discount_rate: percentPayload(editForm.discount_rate),
    price_inflation_rate: percentPayload(editForm.price_inflation_rate),
    jd_self_operated_price: nullable(editForm.jd_self_operated_price),
    tax_code: nullable(editForm.tax_code),
    invoice_name: nullable(editForm.invoice_name),
    tax_category: nullable(editForm.tax_category),
    shipping_courier: nullable(editForm.shipping_courier),
    after_sales_policy: nullable(editForm.after_sales_policy),
  }
  submitting.value = true
  try {
    product.value = await productApi.update(productId.value, payload)
    editVisible.value = false
    ElMessage.success("商品基础资料已更新")
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "更新商品失败")
  } finally {
    submitting.value = false
  }
}

function uniqueNames(values: string[]): string[] { return Array.from(new Set(values)).sort() }
function selectedOption(level: ProductCategoryFilterOption["level"], name: string): ProductCategoryFilterOption | undefined {
  return categoryOptions[level].find((item) => (item.label.split(" / ").at(-1) ?? item.label) === name || item.level1_label === name)
}
function parentCategorySelections(level: ProductCategoryFilterOption["level"]): string[] {
  const level1 = selectedOption("LEVEL1", categoryLevel1.value)
  if (level === "LEVEL1" || !level1) return []
  if (level === "LEVEL2") return [level1.level1_selection_key]
  const level2 = selectedOption("LEVEL2", categoryLevel2.value)
  return level2 ? [level2.level2_selection_key] : [level1.level1_selection_key]
}
async function loadCategoryOptions(level: ProductCategoryFilterOption["level"], keyword = ""): Promise<void> {
  const result = await productApi.categoryFilterOptions(
    level, keyword, 0, parentCategorySelections(level), "ACTIVE",
  )
  categoryOptions[level] = result.items
}
function changeCategoryLevel1(): void {
  categoryLevel2.value = ""
  categoryLevel3.value = ""
  categoryOptions.LEVEL2 = []
  categoryOptions.LEVEL3 = []
  void loadCategoryOptions("LEVEL2")
}
function changeCategoryLevel2(): void {
  categoryLevel3.value = ""
  categoryOptions.LEVEL3 = []
  void loadCategoryOptions("LEVEL3")
}

async function updateImage(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ""
  if (!file) return
  submitting.value = true
  try { product.value = await productApi.updateImage(productId.value, file); ElMessage.success("商品图片已更新") }
  catch (error) { ElMessage.error(error instanceof HttpError ? error.response.message : "更新商品图片失败") }
  finally { submitting.value = false }
}

async function clearImage(): Promise<void> {
  submitting.value = true
  try { product.value = await productApi.clearImage(productId.value); ElMessage.success("商品图片已清除") }
  catch (error) { ElMessage.error(error instanceof HttpError ? error.response.message : "清除商品图片失败") }
  finally { submitting.value = false }
}

onMounted(() => void loadProduct())
</script>

<template>
  <div class="product-detail" v-loading="loading">
    <template v-if="product">
      <header class="page-heading">
        <div>
          <p>PRODUCT MASTER</p>
          <h1>{{ product.product_name ?? "未命名商品" }}</h1>
          <span>{{ product.brand ?? "—" }} · {{ product.model ?? "—" }} · {{ product.sku ?? "—" }}</span>
        </div>
        <div>
          <el-button @click="$router.back()">返回列表</el-button>
          <el-button v-if="canUpdate" @click="openEdit">编辑基础资料</el-button>
          <el-button v-if="canUpdateCost" type="primary" @click="editCostVisible = true">修改成本价</el-button>
        </div>
      </header>

      <el-card class="page-card">
        <template #header><strong>基础信息</strong></template>
        <el-descriptions :column="2" border>
          <el-descriptions-item v-if="imageUrl" label="商品图片" :span="2">
            <el-image class="product-image" :src="imageUrl" fit="contain" :preview-src-list="[imageUrl]" preview-teleported />
          </el-descriptions-item>
          <el-descriptions-item label="所属公司">{{ product.company_name ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="上架日期">{{ product.listed_at ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="品牌">{{ product.brand ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="型号">{{ product.model ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="SKU">{{ product.sku ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="商品名称">{{ product.product_name ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="三级类目" :span="2">{{ [product.category_level1_name, product.category_level2_name, product.category_level3_name].filter(Boolean).join(" / ") || "—" }}</el-descriptions-item>
          <el-descriptions-item label="来源供应商">{{ product.source_supplier_name ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="货号">{{ product.item_number ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="69码">{{ product.barcode_text ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="3C编码">{{ product.certification_3c_code ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="采销员">{{ product.purchasing_agent ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="产品规格" :span="2">{{ product.product_specification ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="卖点" :span="2">{{ product.selling_points ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="包装清单" :span="2">{{ product.packaging_list ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="质保期">{{ product.warranty_period ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="销量">{{ product.sales_volume ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="好评率">{{ percent(product.positive_rating) }}</el-descriptions-item>
          <el-descriptions-item label="店铺类型">{{ product.storefront_type ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="商品链接"><a v-if="product.jd_same_product_url" :href="product.jd_same_product_url" target="_blank">打开链接</a><span v-else>—</span></el-descriptions-item>
          <el-descriptions-item label="参考链接"><a v-if="product.reference_url" :href="product.reference_url" target="_blank">打开链接</a><span v-else>—</span></el-descriptions-item>
          <el-descriptions-item label="限售区域" :span="2">{{ product.restricted_regions ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="税收编码">{{ product.tax_code ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="开票名称">{{ product.invoice_name ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="税收分类">{{ product.tax_category ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="发货快递">{{ product.shipping_courier ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="售后政策" :span="2">{{ product.after_sales_policy ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ product.remark ?? "—" }}</el-descriptions-item>
        </el-descriptions>
      </el-card>

      <el-card class="page-card">
        <template #header><strong>当前价格（固定大表直存）</strong></template>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="当前成本价">{{ money(product.cost_price) }}</el-descriptions-item>
          <el-descriptions-item label="京东价">{{ money(product.jd_price) }}</el-descriptions-item>
          <el-descriptions-item label="京东自营前台价">{{ money(product.jd_self_operated_price) }}</el-descriptions-item>
          <el-descriptions-item label="市场价">{{ money(product.market_price) }}</el-descriptions-item>
          <el-descriptions-item label="协议价">{{ money(product.agreement_price) }}</el-descriptions-item>
          <el-descriptions-item label="协议采购价">{{ money(product.agreement_purchase_price) }}</el-descriptions-item>
          <el-descriptions-item label="利润">{{ money(product.profit) }}</el-descriptions-item>
          <el-descriptions-item label="京东价毛利">{{ percent(product.jd_margin) }}</el-descriptions-item>
          <el-descriptions-item label="毛利率">{{ percent(product.gross_margin) }}</el-descriptions-item>
          <el-descriptions-item label="扣点复核">{{ percent(product.deduction_review) }}</el-descriptions-item>
          <el-descriptions-item label="折扣率">{{ percent(product.discount_rate) }}</el-descriptions-item>
          <el-descriptions-item label="价格虚高比例">{{ percent(product.price_inflation_rate) }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </template>

    <el-dialog v-model="editCostVisible" title="修改当前成本价" width="420px" :close-on-click-modal="false">
      <p class="dialog-tip">此操作只修改成本价，市场价、京东价、协议价、利润及各比例均保持原值。固定大表重新导入会按 Excel 原值逐列覆盖。</p>
      <el-input v-model="form.cost_price" inputmode="decimal" placeholder="例如：123.4567">
        <template #prepend>¥</template>
      </el-input>
      <template #footer>
        <el-button @click="editCostVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="updateCost">确认更新</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑商品主数据" width="920px" :close-on-click-modal="!submitting" :close-on-press-escape="!submitting" :show-close="!submitting">
      <p class="dialog-tip">供应商与 SKU 是商品业务键，不可修改。所有价格和比例均为独立主数据值，可分别维护；“修改成本价”仅更新成本价本身。</p>
      <el-form label-width="105px" class="edit-form">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="上架日期"><el-date-picker v-model="editForm.listed_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="所属公司"><el-input v-model="editForm.company_name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="来源供应商"><el-input :model-value="product?.source_supplier_name ?? ''" disabled /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="SKU"><el-input :model-value="product?.sku ?? ''" disabled /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="商品名称"><el-input v-model="editForm.product_name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="品牌"><el-input v-model="editForm.brand" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="型号"><el-input v-model="editForm.model" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="一级类目" required><el-select v-model="categoryLevel1" filterable allow-create clearable remote :remote-method="(query: string) => loadCategoryOptions('LEVEL1', query)" placeholder="输入或选择一级类目" style="width: 100%" @focus="loadCategoryOptions('LEVEL1')" @change="changeCategoryLevel1"><el-option v-for="name in level1Options" :key="name" :label="name" :value="name" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="二级类目" required><el-select v-model="categoryLevel2" filterable allow-create clearable remote :remote-method="(query: string) => loadCategoryOptions('LEVEL2', query)" placeholder="输入或选择二级类目" :disabled="!categoryLevel1" style="width: 100%" @focus="loadCategoryOptions('LEVEL2')" @change="changeCategoryLevel2"><el-option v-for="name in level2Options" :key="name" :label="name" :value="name" /></el-select></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="三级类目" required><el-select v-model="categoryLevel3" filterable allow-create clearable remote :remote-method="(query: string) => loadCategoryOptions('LEVEL3', query)" placeholder="输入或选择三级类目" :disabled="!categoryLevel2" style="width: 100%" @focus="loadCategoryOptions('LEVEL3')"><el-option v-for="name in level3Options" :key="name" :label="name" :value="name" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="货号"><el-input v-model="editForm.item_number" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="69码"><el-input v-model="editForm.barcode_text" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="3C编码"><el-input v-model="editForm.certification_3c_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="采销员"><el-input v-model="editForm.purchasing_agent" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="店铺类型"><el-input v-model="editForm.storefront_type" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="质保期"><el-input v-model="editForm.warranty_period" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="商品图片"><el-button :loading="submitting" @click="imageInput?.click()">上传替换图片</el-button><el-button v-if="product?.image_reference" :loading="submitting" type="danger" plain @click="clearImage">清除图片</el-button><input ref="imageInput" class="file-input" type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="updateImage" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="商品链接"><el-input v-model="editForm.jd_same_product_url" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="参考链接"><el-input v-model="editForm.reference_url" /></el-form-item></el-col>
          <el-col v-for="field in priceFields" :key="field.key" :span="8"><el-form-item :label="field.label"><el-input v-model="editForm[field.key]" inputmode="decimal" /></el-form-item></el-col>
          <el-col v-for="field in rateFields" :key="field.key" :span="8"><el-form-item :label="`${field.label}（%）`"><el-input v-model="editForm[field.key]" inputmode="decimal" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="销量"><el-input v-model="editForm.sales_volume" inputmode="numeric" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="税收编码"><el-input v-model="editForm.tax_code" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="开票名称"><el-input v-model="editForm.invoice_name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="税收分类"><el-input v-model="editForm.tax_category" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="发货快递"><el-input v-model="editForm.shipping_courier" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="产品规格"><el-input v-model="editForm.product_specification" type="textarea" :rows="2" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="卖点"><el-input v-model="editForm.selling_points" type="textarea" :rows="2" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="包装清单"><el-input v-model="editForm.packaging_list" type="textarea" :rows="2" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="限售区域"><el-input v-model="editForm.restricted_regions" type="textarea" :rows="2" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="售后政策"><el-input v-model="editForm.after_sales_policy" type="textarea" :rows="2" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="备注"><el-input v-model="editForm.remark" type="textarea" :rows="2" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button :disabled="submitting" @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="updateProduct">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.product-detail { display: grid; gap: 18px; }
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 24px 28px; border: 1px solid #dce9fa; border-radius: 14px; background: linear-gradient(115deg, #fff, #edf5ff); }
.page-heading p { margin: 0 0 6px; color: var(--brand-600); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.page-heading h1 { margin: 0 0 8px; color: #172b4d; font-size: 25px; }
.page-heading span, .dialog-tip { color: var(--text-secondary); font-size: 14px; }
.dialog-tip { margin-top: 0; line-height: 1.7; }
.product-image { width: 180px; height: 180px; border: 1px solid var(--border-color); border-radius: 8px; }
.edit-form { max-height: 62vh; overflow-y: auto; padding-right: 8px; }
.file-input { display: none; }
</style>
