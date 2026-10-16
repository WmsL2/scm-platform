<script setup lang="ts">
import { ref, watch } from "vue"
import { ElMessage } from "element-plus"
import { bidApi } from "../../api/bid"
import { productApi } from "../../api/catalog"
import { HttpError } from "../../shared/http"
import type { BidProjectDetail } from "../../types/bid"
import type { ProductFilterOption } from "../../types/catalog"

const props = defineProps<{ project: BidProjectDetail | undefined; disabled?: boolean }>()
const emit = defineEmits<{ updated: [project: BidProjectDetail] }>()

const companyNames = ref<string[]>([])
const purchasingAgents = ref<string[]>([])
const companyOptions = ref<ProductFilterOption[]>([])
const purchaserOptions = ref<ProductFilterOption[]>([])
const companyLoading = ref(false)
const purchaserLoading = ref(false)
const saving = ref(false)

function includeSelected(options: ProductFilterOption[], values: string[]): ProductFilterOption[] {
  const known = new Set(options.map((item) => item.value))
  return [...options, ...values.filter((value) => !known.has(value)).map((value) => ({ value, label: value }))]
}

async function loadCompanies(keyword = ""): Promise<void> {
  companyLoading.value = true
  try { companyOptions.value = includeSelected((await productApi.filterOptions("COMPANY", keyword)).items, companyNames.value) }
  catch (error) { ElMessage.error(error instanceof HttpError ? error.response.message : "加载所属公司失败") }
  finally { companyLoading.value = false }
}

async function loadPurchasers(keyword = ""): Promise<void> {
  purchaserLoading.value = true
  try { purchaserOptions.value = includeSelected((await productApi.filterOptions("PURCHASING_AGENT", keyword)).items, purchasingAgents.value) }
  catch (error) { ElMessage.error(error instanceof HttpError ? error.response.message : "加载采销员失败") }
  finally { purchaserLoading.value = false }
}

watch(() => props.project, (project) => {
  companyNames.value = [...(project?.recommendation_company_names ?? [])]
  purchasingAgents.value = [...(project?.recommendation_purchasing_agents ?? [])]
  if (project) { void loadCompanies(); void loadPurchasers() }
}, { immediate: true })

async function save(): Promise<void> {
  if (!props.project) return
  saving.value = true
  try {
    const updated = await bidApi.updateRecommendationScope(props.project.id, {
      company_names: companyNames.value,
      purchasing_agents: purchasingAgents.value,
    })
    emit("updated", updated)
    ElMessage.success("商品选品范围已保存，将在下一次生成时生效")
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "保存商品选品范围失败")
  } finally { saving.value = false }
}
</script>

<template>
  <div class="scope-form">
    <div class="scope-heading"><strong>商品选品范围</strong><span>仅影响下一次生成；不选即在全部可用商品中选品。</span></div>
    <el-form label-position="top" class="scope-fields">
      <el-form-item label="所属公司">
        <el-select v-model="companyNames" multiple filterable remote reserve-keyword collapse-tags collapse-tags-tooltip :remote-method="loadCompanies" :loading="companyLoading" :disabled="disabled" placeholder="不选则不限所属公司">
          <el-option v-for="item in companyOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="采销员">
        <el-select v-model="purchasingAgents" multiple filterable remote reserve-keyword collapse-tags collapse-tags-tooltip :remote-method="loadPurchasers" :loading="purchaserLoading" :disabled="disabled" placeholder="不选则不限采销员">
          <el-option v-for="item in purchaserOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
      </el-form-item>
      <el-form-item class="scope-save"><el-button :loading="saving" :disabled="disabled" @click="save">保存商品范围</el-button></el-form-item>
    </el-form>
    <p>同一字段多选为并集；同时设置所属公司和采销员时取交集。</p>
  </div>
</template>

<style scoped>
.scope-form { padding-bottom: 8px; border-bottom: 1px solid #ebeef5; margin-bottom: 16px; }
.scope-heading { display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px; }.scope-heading span, p { color: #909399; font-size: 13px; }.scope-fields { display: grid; grid-template-columns: minmax(240px, 1fr) minmax(240px, 1fr) auto; gap: 0 16px; }.scope-fields :deep(.el-select) { width: 100%; }.scope-save { align-self: end; } p { margin: 0; } @media (max-width: 767px) { .scope-fields { grid-template-columns: 1fr; }.scope-save { align-self: auto; } }
</style>
