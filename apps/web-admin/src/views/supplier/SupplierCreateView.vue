<script setup lang="ts">
import { ArrowLeft } from "@element-plus/icons-vue"
import { ref } from "vue"
import { ElMessage } from "element-plus"
import { useRouter } from "vue-router"

import SupplierFormFields from "./SupplierFormFields.vue"
import { supplierApi } from "../../api/supplier"
import { HttpError } from "../../shared/http"
import { createSupplierFormDraft, normalizeSupplierDraft, supplierDraftValidationMessage } from "../../types/supplier"

const draft = ref(createSupplierFormDraft())
const router = useRouter()
const submitting = ref(false)

async function save(): Promise<void> {
  const message = supplierDraftValidationMessage(draft.value)
  if (message) return void ElMessage.warning(message)
  submitting.value = true
  try {
    const supplier = await supplierApi.create(normalizeSupplierDraft(draft.value))
    ElMessage.success(`供应商 ${supplier.supplier_code} 已创建`)
    await router.replace(`/suppliers/${supplier.id}`)
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "创建供应商失败")
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="supplier-page">
    <header class="page-heading">
      <div><p>SUPPLIER MASTER</p><h1>新增供应商</h1><span>供应商编码由后端系统自动生成，不能填写。</span></div>
      <RouterLink to="/suppliers"><el-button :icon="ArrowLeft">返回列表</el-button></RouterLink>
    </header>
    <el-card class="page-card"><SupplierFormFields v-model="draft" /><el-button type="primary" :loading="submitting" @click="save">保存供应商</el-button></el-card>
  </div>
</template>

<style scoped>
.supplier-page { display: grid; gap: 18px; }
.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 24px 28px; border: 1px solid #dce9fa; border-radius: 14px; background: linear-gradient(115deg, #fff, #edf5ff); }
.page-heading p { margin: 0 0 6px; color: var(--brand-600); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.page-heading h1 { margin: 0 0 8px; color: #172b4d; font-size: 26px; }.page-heading span { color: var(--text-secondary); font-size: 14px; }
@media (max-width: 640px) { .page-heading { flex-direction: column; } }
</style>
