<script setup lang="ts">
import { Plus, Remove } from "@element-plus/icons-vue"

import type { SupplierFormDraft } from "../../types/supplier"

const draft = defineModel<SupplierFormDraft>({ required: true })

const props = withDefaults(defineProps<{ readonly?: boolean }>(), {
  readonly: false,
})

function addContact(): void {
  draft.value.contacts.push({ contact_name: null, contact_phone: null })
}

function removeContact(index: number): void {
  draft.value.contacts.splice(index, 1)
}
</script>

<template>
  <el-form label-position="top" class="supplier-form">
    <el-form-item label="供应商名称">
      <el-input v-model="draft.supplier_name" :disabled="props.readonly" placeholder="请输入供应商名称" />
    </el-form-item>
    <el-form-item label="主营品牌">
      <el-input v-model="draft.main_brands" :disabled="props.readonly" placeholder="可输入多个品牌文本" />
    </el-form-item>
    <el-form-item label="主要优势">
      <el-input v-model="draft.advantage" :disabled="props.readonly" type="textarea" :rows="4" placeholder="请输入主要优势" />
    </el-form-item>
    <div class="contacts-heading">
      <span>联系人（选填）</span>
      <el-button v-if="!props.readonly" text type="primary" :icon="Plus" @click="addContact">添加联系人</el-button>
    </div>
    <div v-for="(contact, index) in draft.contacts" :key="index" class="contact-grid">
      <el-form-item label="联系人姓名">
        <el-input v-model="contact.contact_name" :disabled="props.readonly" placeholder="姓名或电话至少填写一项" />
      </el-form-item>
      <el-form-item label="联系电话">
        <div class="contact-phone-row">
          <el-input v-model="contact.contact_phone" :disabled="props.readonly" placeholder="姓名或电话至少填写一项" />
          <el-button v-if="!props.readonly" text type="danger" :icon="Remove" circle aria-label="删除联系人" @click="removeContact(index)" />
        </div>
      </el-form-item>
    </div>
  </el-form>
</template>

<style scoped>
.supplier-form { max-width: 760px; }
.contacts-heading { display: flex; align-items: center; justify-content: space-between; margin: 4px 0 8px; color: #344054; font-size: 14px; font-weight: 600; }
.contact-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.contact-phone-row { display: flex; align-items: center; gap: 6px; }
.contact-phone-row .el-input { min-width: 0; }
@media (max-width: 640px) { .contact-grid { grid-template-columns: 1fr; gap: 0; } }
</style>
