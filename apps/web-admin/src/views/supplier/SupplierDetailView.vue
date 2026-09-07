<script setup lang="ts">
import { ArrowLeft, EditPen } from "@element-plus/icons-vue"
import { computed, onMounted, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { useRoute, useRouter } from "vue-router"

import { supplierApi } from "../../api/supplier"
import { HttpError } from "../../shared/http"
import {
  ARCHIVE_STATUS_LABELS,
  COOPERATION_STATUS_LABELS,
  commandRequiresReason,
  type SupplierCommand,
  type SupplierDetail,
} from "../../types/supplier"
import { useAuthStore } from "../../stores/auth"

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const supplier = ref<SupplierDetail>()
const loading = ref(false)
const executing = ref<SupplierCommand>()
const supplierId = String(route.params.id)

const commands: Array<{ key: SupplierCommand; label: string; permission: string; type?: "warning" | "danger" }> = [
  { key: "submit", label: "提交归档", permission: "supplier:submit" },
  { key: "archive", label: "归档", permission: "supplier:archive" },
  { key: "stop", label: "停用", permission: "supplier:stop", type: "warning" },
  { key: "blacklist", label: "加入黑名单", permission: "supplier:blacklist", type: "danger" },
]

const availableCommands = computed(() =>
  commands.filter((command) => auth.hasPermission(command.permission) && isAvailable(command.key)),
)

function isAvailable(command: SupplierCommand): boolean {
  if (!supplier.value) return false
  if (command === "submit") return supplier.value.archive_status === "DRAFT"
  if (command === "archive") return supplier.value.archive_status === "PENDING"
  return supplier.value.cooperation_status === "NORMAL"
}

function contactsText(current: SupplierDetail): string {
  return current.contacts.length
    ? current.contacts.map((contact) => [contact.contact_name, contact.contact_phone].filter(Boolean).join(" / ")).join("；")
    : "--"
}

async function load(): Promise<void> {
  loading.value = true
  try {
    supplier.value = await supplierApi.get(supplierId)
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载供应商失败")
    await router.replace("/suppliers")
  } finally {
    loading.value = false
  }
}

async function execute(command: SupplierCommand): Promise<void> {
  if (!supplier.value) return
  try {
    let reason: string | undefined
    if (commandRequiresReason(command)) {
      const result = await ElMessageBox.prompt("请填写操作原因", command === "stop" ? "停用供应商" : "加入黑名单", {
        confirmButtonText: "确认",
        cancelButtonText: "取消",
        inputPattern: /\S+/,
        inputErrorMessage: "必须填写原因",
      })
      reason = result.value.trim()
    } else {
      await ElMessageBox.confirm(
        command === "submit" ? "确认提交归档申请吗？" : "确认将供应商归档吗？",
        command === "submit" ? "提交归档" : "归档供应商",
        { confirmButtonText: "确认", cancelButtonText: "取消", type: "warning" },
      )
    }
    executing.value = command
    supplier.value = await supplierApi.command(supplier.value.id, command, reason)
    ElMessage.success("状态操作已完成")
  } catch (error) {
    if (error === "cancel" || error === "close") return
    ElMessage.error(error instanceof HttpError ? error.response.message : "状态操作失败")
  } finally {
    executing.value = undefined
  }
}

onMounted(() => void load())
</script>

<template>
  <div class="supplier-page">
    <header class="page-heading">
      <div><p>SUPPLIER MASTER</p><h1>供应商详情</h1><span>查看供应商基础资料、归档和合作状态。</span></div>
      <div class="header-actions">
        <RouterLink v-if="supplier && auth.hasPermission('supplier:update')" :to="`${$route.path}/edit`"><el-button :icon="EditPen">编辑</el-button></RouterLink>
        <RouterLink to="/suppliers"><el-button :icon="ArrowLeft">返回列表</el-button></RouterLink>
      </div>
    </header>
    <el-card v-loading="loading" class="page-card">
      <template #header><strong>基本资料</strong></template>
      <el-descriptions v-if="supplier" :column="2" border>
        <el-descriptions-item label="供应商编码">{{ supplier.supplier_code }}</el-descriptions-item>
        <el-descriptions-item label="供应商名称">{{ supplier.supplier_name }}</el-descriptions-item>
        <el-descriptions-item label="主营品牌">{{ supplier.main_brands }}</el-descriptions-item>
        <el-descriptions-item label="主要优势">{{ supplier.advantage }}</el-descriptions-item>
        <el-descriptions-item label="联系人" :span="2">{{ contactsText(supplier) }}</el-descriptions-item>
        <el-descriptions-item label="归档状态"><el-tag effect="plain">{{ ARCHIVE_STATUS_LABELS[supplier.archive_status] }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="合作状态"><el-tag :type="supplier.cooperation_status === 'NORMAL' ? 'success' : supplier.cooperation_status === 'STOPPED' ? 'warning' : 'danger'" effect="plain">{{ COOPERATION_STATUS_LABELS[supplier.cooperation_status] }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ new Date(supplier.created_at).toLocaleString() }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ new Date(supplier.updated_at).toLocaleString() }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else-if="!loading" description="未找到供应商" :image-size="72" />
    </el-card>
    <el-card v-if="supplier" class="page-card">
      <template #header><strong>状态操作</strong></template>
      <div class="command-area">
        <div v-for="command in availableCommands" :key="command.key" class="command-item">
          <div><strong>{{ command.label }}</strong><small v-if="commandRequiresReason(command.key)">后续操作时必须填写原因</small></div>
          <el-button :type="command.type" :loading="executing === command.key" :disabled="Boolean(executing)" @click="execute(command.key)">{{ command.label }}</el-button>
        </div>
        <el-empty v-if="availableCommands.length === 0" description="当前状态下没有可执行的供应商操作" :image-size="72" />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.supplier-page { display: grid; gap: 18px; }.page-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 24px 28px; border: 1px solid #dce9fa; border-radius: 14px; background: linear-gradient(115deg, #fff, #edf5ff); }.page-heading p { margin: 0 0 6px; color: var(--brand-600); font-size: 12px; font-weight: 700; letter-spacing: .08em; }.page-heading h1 { margin: 0 0 8px; color: #172b4d; font-size: 26px; }.page-heading span { color: var(--text-secondary); font-size: 14px; }.header-actions { display: flex; gap: 10px; }.command-area { display: grid; }.command-item { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 13px 0; border-bottom: 1px solid var(--border); }.command-item:last-child { border-bottom: 0; }.command-item strong { display: block; color: #344054; font-size: 14px; }.command-item small { display: block; margin-top: 4px; color: #98a2b3; font-size: 12px; } @media (max-width: 640px) { .page-heading, .command-item { flex-direction: column; align-items: flex-start; } }
</style>
