<script setup lang="ts">
import { onMounted, ref } from "vue"
import { ElMessage, ElMessageBox, type TabPaneName } from "element-plus"

import { accountApi } from "../../api/account"
import { userStatusLabel, userStatusTagType } from "../../shared/account/user-status"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import { useRegistrationStore } from "../../stores/registration"
import type { AccountUser } from "../../types/account"

const auth = useAuthStore()
const registration = useRegistrationStore()
const activeTab = ref<"pending" | "history">("pending")
const pendingRows = ref<AccountUser[]>([])
const pendingTotal = ref(0)
const historyRows = ref<AccountUser[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = 20
const pendingLoading = ref(false)
const historyLoading = ref(false)

async function loadPending(): Promise<void> {
  pendingLoading.value = true
  try {
    const result = await accountApi.registrations()
    pendingRows.value = result.items
    pendingTotal.value = result.total
    registration.setPendingCount(result.total)
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载待审批申请失败")
  } finally {
    pendingLoading.value = false
  }
}

async function loadHistory(page = historyPage.value): Promise<void> {
  historyLoading.value = true
  try {
    const result = await accountApi.registrationHistory(page, historyPageSize)
    historyRows.value = result.items
    historyTotal.value = result.total
    historyPage.value = result.page
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载审批历史失败")
  } finally {
    historyLoading.value = false
  }
}

function handleTabChange(tab: TabPaneName): void {
  if (tab === "history") void loadHistory(1)
}

function formatReviewTime(value: string | null): string {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false })
}

async function review(row: AccountUser, approve: boolean): Promise<void> {
  try {
    let note: string | undefined
    if (!approve) note = (await ElMessageBox.prompt("拒绝原因", "拒绝")).value
    await accountApi.review(row.id, approve, note)
    ElMessage.success(approve ? "已批准注册申请" : "已拒绝注册申请")
    await Promise.all([loadPending(), loadHistory(1)])
  } catch (error) {
    if (error instanceof HttpError) {
      ElMessage.error(error.status === 409 ? "该注册申请状态已发生变化，请刷新后查看最新状态。" : error.response.message)
    }
  }
}

onMounted(() => void loadPending())
</script>

<template>
  <el-card class="registration-card">
    <h2>注册审批</h2>
    <el-tabs v-model="activeTab" class="registration-tabs" @tab-change="handleTabChange">
      <el-tab-pane :label="`待审批（${pendingTotal}）`" name="pending">
        <el-table v-loading="pendingLoading" :data="pendingRows" empty-text="暂无待审批申请">
          <el-table-column prop="username" label="用户名" min-width="180" />
          <el-table-column label="状态" min-width="140">
            <template #default="{ row }">
              <el-tag :type="userStatusTagType(row.user_status)" effect="plain">
                {{ userStatusLabel(row.user_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200">
            <template #default="{ row }">
              <template v-if="auth.hasPermission('system:registration:review')">
                <el-button type="primary" plain @click="review(row, true)">批准</el-button>
                <el-button type="danger" plain @click="review(row, false)">拒绝</el-button>
              </template>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="审批历史" name="history">
        <el-table v-loading="historyLoading" :data="historyRows" empty-text="暂无审批历史">
          <el-table-column prop="username" label="用户名" min-width="180" />
          <el-table-column label="审批结果" min-width="140">
            <template #default="{ row }">
              <el-tag :type="userStatusTagType(row.user_status)" effect="plain">
                {{ userStatusLabel(row.user_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="审批时间" min-width="190">
            <template #default="{ row }">{{ formatReviewTime(row.reviewed_at) }}</template>
          </el-table-column>
          <el-table-column label="审批说明" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">{{ row.review_note || "—" }}</template>
          </el-table-column>
        </el-table>
        <div class="history-pagination">
          <el-pagination
            background
            layout="total, prev, pager, next"
            :current-page="historyPage"
            :page-size="historyPageSize"
            :total="historyTotal"
            @current-change="loadHistory"
          />
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<style scoped>
.registration-card :deep(.el-card__body) { padding: 24px 28px; }
.registration-card h2 { margin: 0 0 14px; color: var(--text-primary); }
.registration-tabs :deep(.el-tabs__header) { margin-bottom: 18px; }
.history-pagination { display: flex; justify-content: flex-end; margin-top: 16px; }
</style>
