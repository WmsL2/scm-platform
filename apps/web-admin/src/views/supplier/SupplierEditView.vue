<script setup lang="ts">
import { ArrowLeft } from "@element-plus/icons-vue"
import { onMounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { useRoute, useRouter } from "vue-router"

import SupplierFormFields from "./SupplierFormFields.vue"
import { supplierApi } from "../../api/supplier"
import { HttpError } from "../../shared/http"
import {
  createSupplierFormDraft,
  normalizeSupplierDraft,
  supplierDetailToDraft,
  supplierDraftValidationMessage,
} from "../../types/supplier"

const draft = ref(createSupplierFormDraft())
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const supplierId = String(route.params.id)

async function load(): Promise<void> {
  loading.value = true
  try {
    draft.value = supplierDetailToDraft(await supplierApi.get(supplierId))
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载供应商失败")
    await router.replace("/suppliers")
  } finally {
    loading.value = false
  }
}

async function save(): Promise<void> {
  const message = supplierDraftValidationMessage(draft.value)
  if (message) return void ElMessage.warning(message)
  submitting.value = true
  try {
    const supplier = await supplierApi.update(supplierId, normalizeSupplierDraft(draft.value))
    ElMessage.success("供应商资料已保存")
    await router.replace(`/suppliers/${supplier.id}`)
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "保存供应商失败")
  } finally {
    submitting.value = false
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="supplier-page">
    <header class="page-heading">
      <div><p>SUPPLIER MASTER</p><h1>编辑供应商</h1><span>供应商编码由系统生成不可修改；可按实际业务调整归档状态。</span></div>
      <RouterLink :to="$route.path.replace(/\/edit$/, '')"><el-button :icon="ArrowLeft">返回详情</el-button></RouterLink>
    </header>
    <el-card v-loading="loading" class="page-card"><SupplierFormFields v-model="draft" /><el-button type="primary" :loading="submitting" :disabled="loading" @click="save">保存修改</el-button></el-card>
  </div>
</template>

<style scoped>
.supplier-page { display: grid; gap: 18px; }.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 24px 28px; border: 1px solid #dce9fa; border-radius: 14px; background: linear-gradient(115deg, #fff, #edf5ff); }.page-heading p { margin: 0 0 6px; color: var(--brand-600); font-size: 12px; font-weight: 700; letter-spacing: .08em; }.page-heading h1 { margin: 0 0 8px; color: #172b4d; font-size: 26px; }.page-heading span { color: var(--text-secondary); font-size: 14px; } @media (max-width: 640px) { .page-heading { flex-direction: column; } }
</style>
