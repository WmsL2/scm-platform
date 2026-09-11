<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { ElMessage } from "element-plus"

import { productApi } from "../../api/catalog"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type {
  ProductDetail,
  ProductSourceSupplierCandidate,
  ProductUpdatePayload,
} from "../../types/catalog"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(false)
const submitting = ref(false)
const product = ref<ProductDetail | null>(null)
const editCostVisible = ref(route.query.editCost === "1")
const editVisible = ref(false)
const supplierCandidates = ref<ProductSourceSupplierCandidate[]>([])
const form = reactive({ cost_price: "" })
const editForm = reactive({
  listed_at: "",
  brand: "",
  image_reference: "",
  model: "",
  sku: "",
  product_name: "",
  item_number: "",
  jd_same_product_url: "",
  purchasing_agent: "",
  source_supplier_id: "",
  barcode_text: "",
  product_specification: "",
  selling_points: "",
  remark: "",
  restricted_regions: "",
  reference_url: "",
  storefront_type: "",
})
const productId = computed(() => String(route.params.id))
const canUpdateCost = computed(
  () => auth.hasPermission("product:cost:update") && product.value?.category_id,
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
    form.cost_price = product.value.cost_price
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载商品详情失败")
  } finally {
    loading.value = false
  }
}

function money(value: string | null): string {
  return value === null ? "—" : `¥ ${value}`
}

async function updateCost(): Promise<void> {
  submitting.value = true
  try {
    product.value = await productApi.updateCost(productId.value, form.cost_price)
    ElMessage.success("成本价和派生定价已同步更新")
    editCostVisible.value = false
    await router.replace({ query: {} })
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "更新成本价失败")
  } finally {
    submitting.value = false
  }
}

function populateEditForm(item: ProductDetail): void {
  editForm.listed_at = item.listed_at ?? ""
  editForm.brand = item.brand ?? ""
  editForm.image_reference = item.image_reference ?? ""
  editForm.model = item.model ?? ""
  editForm.sku = item.sku ?? ""
  editForm.product_name = item.product_name ?? ""
  editForm.item_number = item.item_number ?? ""
  editForm.jd_same_product_url = item.jd_same_product_url ?? ""
  editForm.purchasing_agent = item.purchasing_agent ?? ""
  editForm.source_supplier_id = item.source_supplier_id
  editForm.barcode_text = item.barcode_text ?? ""
  editForm.product_specification = item.product_specification ?? ""
  editForm.selling_points = item.selling_points ?? ""
  editForm.remark = item.remark ?? ""
  editForm.restricted_regions = item.restricted_regions ?? ""
  editForm.reference_url = item.reference_url ?? ""
  editForm.storefront_type = item.storefront_type ?? ""
}

function nullable(value: string): string | null {
  const normalized = value.trim()
  return normalized || null
}

async function openEdit(): Promise<void> {
  if (!product.value || submitting.value) return
  submitting.value = true
  try {
    supplierCandidates.value = await productApi.sourceSupplierCandidates()
    populateEditForm(product.value)
    editVisible.value = true
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载可选供应商失败")
  } finally {
    submitting.value = false
  }
}

async function updateProduct(): Promise<void> {
  if (!editForm.sku.trim()) {
    ElMessage.warning("SKU不能为空")
    return
  }
  if (!editForm.source_supplier_id) {
    ElMessage.warning("请选择来源供应商")
    return
  }
  const payload: ProductUpdatePayload = {
    listed_at: nullable(editForm.listed_at),
    brand: nullable(editForm.brand),
    image_reference: nullable(editForm.image_reference),
    model: nullable(editForm.model),
    sku: editForm.sku.trim(),
    product_name: nullable(editForm.product_name),
    item_number: nullable(editForm.item_number),
    jd_same_product_url: nullable(editForm.jd_same_product_url),
    purchasing_agent: nullable(editForm.purchasing_agent),
    source_supplier_id: editForm.source_supplier_id,
    barcode_text: nullable(editForm.barcode_text),
    product_specification: nullable(editForm.product_specification),
    selling_points: nullable(editForm.selling_points),
    remark: nullable(editForm.remark),
    restricted_regions: nullable(editForm.restricted_regions),
    reference_url: nullable(editForm.reference_url),
    storefront_type: nullable(editForm.storefront_type),
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
          <el-button v-if="canUpdateCost" type="primary" @click="editCostVisible = true">更新成本价</el-button>
        </div>
      </header>

      <el-card class="page-card">
        <template #header><strong>基础信息</strong></template>
        <el-descriptions :column="2" border>
          <el-descriptions-item v-if="imageUrl" label="商品图片" :span="2">
            <el-image class="product-image" :src="imageUrl" fit="contain" :preview-src-list="[imageUrl]" preview-teleported />
          </el-descriptions-item>
          <el-descriptions-item label="三级类目">{{ [product.category_level1_name, product.category_level2_name, product.category_level3_name].filter(Boolean).join(" / ") || "—" }}</el-descriptions-item>
          <el-descriptions-item label="受控类目关联">{{ product.category ? "已关联" : "固定大表直存，未关联" }}</el-descriptions-item>
          <el-descriptions-item label="来源供应商">{{ product.source_supplier_name ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="货号">{{ product.item_number ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="69码">{{ product.barcode_text ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="采销员">{{ product.purchasing_agent ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="产品规格" :span="2">{{ product.product_specification ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="卖点" :span="2">{{ product.selling_points ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="店铺类型">{{ product.storefront_type ?? "—" }}</el-descriptions-item>
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
          <el-descriptions-item label="京东价毛利">{{ product.jd_margin ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="众诚毛利">{{ product.gross_margin ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="毛利复核">{{ product.deduction_review ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="折扣率">{{ product.discount_rate ?? "—" }}</el-descriptions-item>
          <el-descriptions-item label="价格虚高比例">{{ product.price_inflation_rate ?? "—" }}</el-descriptions-item>
        </el-descriptions>
      </el-card>
    </template>

    <el-dialog v-model="editCostVisible" title="更新当前成本价" width="420px" :close-on-click-modal="false">
      <p class="dialog-tip">此独立维护操作会原子重算价格字段；固定大表导入不会重算或覆盖 Excel 价格。</p>
      <el-input v-model="form.cost_price" inputmode="decimal" placeholder="例如：123.4567">
        <template #prepend>¥</template>
      </el-input>
      <template #footer>
        <el-button @click="editCostVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="updateCost">确认更新</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑商品基础资料" width="820px" :close-on-click-modal="!submitting" :close-on-press-escape="!submitting" :show-close="!submitting">
      <p class="dialog-tip">类目和价格为受控字段；成本价请使用“更新成本价”并由系统重算派生价格。</p>
      <el-form label-width="105px" class="edit-form">
        <el-row :gutter="16">
          <el-col :span="12"><el-form-item label="上架日期"><el-date-picker v-model="editForm.listed_at" type="date" value-format="YYYY-MM-DD" style="width: 100%" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="来源供应商" required><el-select v-model="editForm.source_supplier_id" filterable style="width: 100%"><el-option v-for="supplier in supplierCandidates" :key="supplier.id" :label="`${supplier.supplier_name}（${supplier.supplier_code}）`" :value="supplier.id" /></el-select></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="商品名称"><el-input v-model="editForm.product_name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="SKU" required><el-input v-model="editForm.sku" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="品牌"><el-input v-model="editForm.brand" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="型号"><el-input v-model="editForm.model" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="货号"><el-input v-model="editForm.item_number" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="69码"><el-input v-model="editForm.barcode_text" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="采销员"><el-input v-model="editForm.purchasing_agent" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="店铺类型"><el-input v-model="editForm.storefront_type" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="图片地址"><el-input v-model="editForm.image_reference" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="商品链接"><el-input v-model="editForm.jd_same_product_url" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="参考链接"><el-input v-model="editForm.reference_url" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="产品规格"><el-input v-model="editForm.product_specification" type="textarea" :rows="2" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="卖点"><el-input v-model="editForm.selling_points" type="textarea" :rows="2" /></el-form-item></el-col>
          <el-col :span="24"><el-form-item label="限售区域"><el-input v-model="editForm.restricted_regions" type="textarea" :rows="2" /></el-form-item></el-col>
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
</style>
