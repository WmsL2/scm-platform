<script setup lang="ts">
import { computed, markRaw, onMounted } from "vue"
import { Box, DataAnalysis, Document, OfficeBuilding } from "@element-plus/icons-vue"
import { useRouter } from "vue-router"

import { useAuthStore } from "../../stores/auth"
import { useDashboardStore } from "../../stores/dashboard"
import {
  PROJECT_STATUS_LABELS,
  PROJECT_TYPE_LABELS,
  type BidProjectStatus,
  type BidProjectType,
} from "../../types/bid"
import type { DashboardRecentProject, DashboardSummary } from "../../types/dashboard"

const auth = useAuthStore()
const dashboard = useDashboardStore()
const router = useRouter()
const summary = computed<DashboardSummary | undefined>(() => dashboard.summary)
const summaryLoading = computed(() => dashboard.loading)
const summaryLoadFailed = computed(() => dashboard.loadFailed)

const summaryCards = computed(() => [
  { label: "正式商品", value: summary.value?.formal_product_count, note: "可用于查询和选品的商品", icon: markRaw(Box), tone: "blue" },
  { label: "正常合作供应商", value: summary.value?.normal_supplier_count, note: "已归档且正常合作", icon: markRaw(OfficeBuilding), tone: "indigo" },
  { label: "进行中的项目", value: summary.value?.active_project_count, note: "待处理、选品或投标中的项目", icon: markRaw(DataAnalysis), tone: "cyan" },
  { label: "待处理事项", value: undefined, note: "待办处理流程跑通后接入", icon: markRaw(Document), tone: "amber" },
])

const quickActions = computed(() => [
  { title: "商品主数据", description: "查询、维护和导入商品", path: "/products", permission: "product:list", icon: markRaw(Box) },
  { title: "导入商品 Excel", description: "直接选择商品大表并预览", path: "/products?action=import", permission: "product:import", icon: markRaw(Document) },
  { title: "供应商管理", description: "维护供应商及合作状态", path: "/suppliers", permission: "supplier:list", icon: markRaw(OfficeBuilding) },
  { title: "导入供应商 Excel", description: "直接选择供应商表并预览", path: "/suppliers?action=import", permission: "supplier:create", icon: markRaw(Document) },
  { title: "新增供应商", description: "录入新的供应商资料", path: "/suppliers/new", permission: "supplier:create", icon: markRaw(OfficeBuilding) },
  { title: "投标与推品项目", description: "继续选品或查看项目结果", path: "/bid-projects", permission: "bid:list", icon: markRaw(DataAnalysis) },
  { title: "新建项目", description: "创建条件筛选或自由推品项目", path: "/bid-projects?action=create", permission: "bid:create", icon: markRaw(Document) },
].filter((action) => auth.hasPermission(action.permission)))

async function loadSummary(): Promise<void> {
  await dashboard.refresh()
}

function cardValue(value: number | undefined): string {
  if (summaryLoadFailed.value) return "--"
  return value === undefined ? "--" : value.toLocaleString("zh-CN")
}

function projectTarget(project: DashboardRecentProject): string {
  return project.project_type === "FREE_RECOMMENDATION"
    ? `/bid-projects/${project.id}/recommendation`
    : `/bid-projects/${project.id}`
}

function statusTagType(status: BidProjectStatus): "success" | "warning" | "info" | "primary" {
  if (status === "WON") return "success"
  if (status === "LOST" || status === "VOIDED") return "info"
  if (status === "READY" || status === "EXPORTED" || status === "SUBMITTED") return "warning"
  return "primary"
}

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date)
}

onMounted(() => void loadSummary())
</script>

<template>
  <div class="dashboard-page">
    <section class="welcome-banner">
      <div>
        <p>企业工作台</p>
        <h1>你好，{{ auth.username }}</h1>
        <span>欢迎回来，今天可以从商品维护、供应商管理或项目选品开始工作。</span>
      </div>
      <el-button :loading="summaryLoading" @click="loadSummary">刷新数据</el-button>
    </section>

    <section class="summary-grid">
      <article v-for="card in summaryCards" :key="card.label" class="summary-card">
        <div class="summary-icon" :class="card.tone"><el-icon><component :is="card.icon" /></el-icon></div>
        <div>
          <p>{{ card.label }}</p>
          <strong>{{ cardValue(card.value) }}</strong>
          <small>{{ summaryLoadFailed ? "统计加载失败，请稍后刷新" : card.note }}</small>
        </div>
      </article>
    </section>

    <section class="content-grid">
      <el-card class="page-card recent-card">
        <template #header>
          <div class="card-heading">
            <div><strong>最近项目</strong><span>继续处理最近更新的项目</span></div>
            <el-button v-if="auth.hasPermission('bid:list')" link type="primary" @click="router.push('/bid-projects')">查看全部</el-button>
          </div>
        </template>
        <el-table v-if="auth.hasPermission('bid:list') && summary?.recent_projects.length" :data="summary.recent_projects" class="recent-table">
          <el-table-column prop="project_name" label="项目" min-width="190">
            <template #default="{ row }">
              <button class="project-link" type="button" @click="router.push(projectTarget(row))">{{ row.project_name }}</button>
              <small>{{ row.project_code }}</small>
            </template>
          </el-table-column>
          <el-table-column label="类型" min-width="130">
            <template #default="{ row }">{{ PROJECT_TYPE_LABELS[row.project_type as BidProjectType] ?? row.project_type }}</template>
          </el-table-column>
          <el-table-column label="状态" width="105">
            <template #default="{ row }"><el-tag :type="statusTagType(row.status)" effect="light">{{ PROJECT_STATUS_LABELS[row.status] ?? row.status }}</el-tag></template>
          </el-table-column>
          <el-table-column label="最近更新" width="125">
            <template #default="{ row }">{{ formatTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column width="76" align="right">
            <template #default="{ row }"><el-button link type="primary" @click="router.push(projectTarget(row))">继续</el-button></template>
          </el-table-column>
        </el-table>
        <el-empty v-else-if="!summaryLoading" :description="auth.hasPermission('bid:list') ? '暂无项目，创建后会显示在这里' : '当前账号暂无项目查看权限'" :image-size="72" />
      </el-card>

      <el-card class="page-card quick-card">
        <template #header>
          <div class="card-heading"><div><strong>快捷入口</strong><span>按当前账号权限显示</span></div></div>
        </template>
        <div v-if="quickActions.length" class="quick-list">
          <button v-for="action in quickActions" :key="action.path" type="button" class="quick-action" @click="router.push(action.path)">
            <span class="quick-icon"><el-icon><component :is="action.icon" /></el-icon></span>
            <span><strong>{{ action.title }}</strong><small>{{ action.description }}</small></span>
            <b>›</b>
          </button>
        </div>
        <el-empty v-else description="当前账号暂无可用业务入口" :image-size="72" />
      </el-card>
    </section>
  </div>
</template>

<style scoped>
.dashboard-page { display: grid; gap: 20px; }
.welcome-banner { display: flex; align-items: flex-start; justify-content: space-between; gap: 24px; padding: 26px 28px; border: 1px solid #dce9fa; border-radius: 14px; background: linear-gradient(115deg, #fff 0%, #f2f7ff 70%, #e8f2ff 100%); box-shadow: var(--shadow-soft); }
.welcome-banner p { margin: 0 0 6px; color: var(--brand-600); font-size: 12px; font-weight: 700; letter-spacing: .08em; }
.welcome-banner h1 { margin: 0 0 9px; color: #172b4d; font-size: 26px; }
.welcome-banner span { color: var(--text-secondary); font-size: 14px; }
.summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.summary-card { display: flex; align-items: flex-start; gap: 15px; min-height: 136px; padding: 20px; border: 1px solid var(--border); border-radius: 12px; background: #fff; box-shadow: 0 6px 18px rgba(31, 54, 88, .04); }
.summary-icon { display: grid; width: 43px; height: 43px; flex: none; place-items: center; border-radius: 11px; font-size: 20px; }
.summary-icon.blue { color: #1e67cf; background: #eaf3ff; } .summary-icon.indigo { color: #635bdb; background: #f0efff; } .summary-icon.cyan { color: #0784a7; background: #e8f8fb; } .summary-icon.amber { color: #c67b0a; background: #fff5df; }
.summary-card p { margin: 1px 0 8px; color: #667085; font-size: 13px; }
.summary-card strong { display: block; margin-bottom: 6px; color: #1d2939; font-size: 25px; }
.summary-card small { color: #98a2b3; font-size: 11px; line-height: 1.5; }
.content-grid { display: grid; grid-template-columns: minmax(0, 1.45fr) minmax(310px, .55fr); gap: 16px; }
.card-heading { display: flex; align-items: center; justify-content: space-between; }
.card-heading > div { display: grid; gap: 4px; }
.card-heading strong { color: #243653; font-size: 15px; }
.card-heading span { color: #98a2b3; font-size: 12px; }
.recent-table :deep(.el-table__cell) { padding: 12px 0; }
.project-link { display: block; max-width: 100%; padding: 0; overflow: hidden; border: 0; color: #243653; background: transparent; font: inherit; font-weight: 600; text-align: left; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
.project-link:hover { color: var(--brand-600); }
.project-link + small { display: block; margin-top: 4px; color: #98a2b3; }
.quick-list { display: grid; gap: 10px; }
.quick-action { display: grid; grid-template-columns: 38px minmax(0, 1fr) auto; align-items: center; gap: 11px; width: 100%; padding: 12px; border: 1px solid #e5eaf1; border-radius: 9px; background: #fff; text-align: left; cursor: pointer; transition: border-color .18s, box-shadow .18s, transform .18s; }
.quick-action:hover { border-color: #a9c9f4; box-shadow: 0 5px 14px rgb(31 103 207 / 9%); transform: translateY(-1px); }
.quick-action > span:nth-child(2) { display: grid; gap: 4px; }
.quick-action strong { color: #344054; font-size: 13px; }
.quick-action small { overflow: hidden; color: #98a2b3; font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }
.quick-action b { color: #98a2b3; font-size: 20px; font-weight: 400; }
.quick-icon { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 9px; color: var(--brand-600); background: #eef5ff; font-size: 18px; }
@media (max-width: 1180px) { .summary-grid { grid-template-columns: repeat(2, 1fr); } .content-grid { grid-template-columns: 1fr; } }
@media (max-width: 680px) { .summary-grid { grid-template-columns: 1fr; } .welcome-banner { flex-direction: column; } }
</style>
