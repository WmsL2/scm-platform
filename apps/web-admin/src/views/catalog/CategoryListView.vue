<script setup lang="ts">
import { onMounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { categoryApi } from "../../api/category"
import type { Category, CategoryImportResult } from "../../types/category"
import { HttpError } from "../../shared/http"
const rows = ref<Category[]>([])
const file = ref<File>()
const deductionRatePercent = ref("8")
const importing = ref(false)
const result = ref<CategoryImportResult>()
async function load(): Promise<void> { rows.value = await categoryApi.list() }
async function upload(): Promise<void> {
  if (!file.value || !deductionRatePercent.value.trim()) return
  importing.value = true
  try { result.value = await categoryApi.import(file.value, deductionRatePercent.value); if (!result.value.failed) await load() }
  catch (error) { ElMessage.error(error instanceof HttpError ? error.response.message : "导入失败") }
  finally { importing.value = false }
}
async function template(): Promise<void> { const blob = await categoryApi.template(); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "商城类目导入模板.xlsx"; link.click(); URL.revokeObjectURL(link.href) }
onMounted(() => void load())
</script>
<template>
  <section><div class="page-header"><h2>类目管理</h2><el-button @click="template">下载模板</el-button></div>
    <el-card><el-button @click="$refs.input?.click()">选择 Excel</el-button><input ref="input" type="file" accept=".xlsx" hidden @change="file = ($event.target as HTMLInputElement).files?.[0]" />
      <span v-if="file">{{ file.name }}</span><el-input v-model="deductionRatePercent" type="number" min="0" max="100" step="0.01" placeholder="本批次扣点率（%）" /><el-button type="primary" :disabled="!file || !deductionRatePercent.trim()" :loading="importing" @click="upload">导入</el-button><p>本次 Excel 中所有新导入类目统一使用该扣点率。Excel 颜色不参与扣点率判断。</p></el-card>
    <el-alert v-if="result" :type="result.failed ? 'error' : 'success'" :closable="false" :title="`总计 ${result.total}，成功 ${result.success}，跳过 ${result.skipped}，失败 ${result.failed}`" />
    <el-table :data="rows"><el-table-column prop="level1_name" label="一级类目"/><el-table-column prop="level2_name" label="二级类目"/><el-table-column prop="level3_name" label="三级类目"/><el-table-column prop="deduction_rate" label="扣点"/></el-table>
    <el-table v-if="result?.errors.length" :data="result.errors"><el-table-column prop="row_number" label="行号"/><el-table-column prop="field" label="字段"/><el-table-column prop="value" label="值"/><el-table-column prop="reason" label="原因"/></el-table>
  </section>
</template>
<style scoped>.page-header{display:flex;justify-content:space-between;margin-bottom:16px}.el-input{width:200px;margin:0 12px}</style>
