<script setup lang="ts">
import { markRaw } from "vue"
import { Box, DataAnalysis, Document, OfficeBuilding } from "@element-plus/icons-vue"

import { isMockMode } from "../../api/auth"
import { useAuthStore } from "../../stores/auth"

const auth = useAuthStore()

const summaryCards = [
  { label: "正式商品", value: "--", note: "等待商品主数据接口", icon: markRaw(Box), tone: "blue" },
  { label: "已归档供应商", value: "--", note: "等待供应商字段冻结", icon: markRaw(OfficeBuilding), tone: "indigo" },
  { label: "有效供应商报价", value: "--", note: "计划于 Sprint 2 建设", icon: markRaw(DataAnalysis), tone: "cyan" },
  { label: "待处理导入", value: "--", note: "计划于 Sprint 4 建设", icon: markRaw(Document), tone: "amber" },
]

const progressItems = [
  { title: "前端认证与后台壳层", description: "登录、状态恢复、路由守卫和工作台", state: "功能已实现", type: "primary" },
  { title: "Auth/RBAC Kernel", description: "login、me、logout 和权限依赖", state: "后端已合入", type: "success" },
  { title: "Business Sequence", description: "供应商永久编码所需的并发安全序列", state: "由后端推进", type: "warning" },
  { title: "Supplier Master", description: "等待真实供应商字段资料确认", state: "Gate 限制", type: "info" },
] as const
</script>

<template>
  <div class="dashboard-page">
    <section class="welcome-banner">
      <div>
        <p>企业工作台</p>
        <h1>你好，{{ auth.username }}</h1>
        <span>当前前端基础能力已就绪，业务数据将在对应接口完成后接入。</span>
      </div>
      <el-tag :type="isMockMode ? 'warning' : 'success'" effect="light" round>
        {{ isMockMode ? "本地 Mock 模式" : "真实 API 模式" }}
      </el-tag>
    </section>

    <section class="summary-grid">
      <article v-for="card in summaryCards" :key="card.label" class="summary-card">
        <div class="summary-icon" :class="card.tone"><el-icon><component :is="card.icon" /></el-icon></div>
        <div>
          <p>{{ card.label }}</p>
          <strong>{{ card.value }}</strong>
          <small>{{ card.note }}</small>
        </div>
      </article>
    </section>

    <section class="content-grid">
      <el-card class="page-card progress-card">
        <template #header>
          <div class="card-heading"><strong>当前建设进度</strong><span>Sprint 1</span></div>
        </template>
        <div class="progress-list">
          <div v-for="item in progressItems" :key="item.title" class="progress-item">
            <span class="progress-dot" />
            <div><strong>{{ item.title }}</strong><p>{{ item.description }}</p></div>
            <el-tag :type="item.type" effect="plain" size="small">{{ item.state }}</el-tag>
          </div>
        </div>
      </el-card>

      <el-card class="page-card boundary-card">
        <template #header>
          <div class="card-heading"><strong>开发边界</strong><span>Local-First</span></div>
        </template>
        <div class="boundary-content">
          <div class="boundary-line"><span>认证数据</span><strong>{{ isMockMode ? "仅本机演示" : "来自 FastAPI" }}</strong></div>
          <div class="boundary-line"><span>业务统计</span><strong>尚未接入</strong></div>
          <div class="boundary-line"><span>供应商字段</span><strong>禁止提前假设</strong></div>
          <div class="boundary-line"><span>正式权限</span><strong>以后端校验为准</strong></div>
          <el-alert title="页面中的 -- 代表暂无可信数据，不使用虚构数字填充。" type="info" :closable="false" show-icon />
        </div>
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
.content-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(320px, .65fr); gap: 16px; }
.card-heading { display: flex; align-items: center; justify-content: space-between; }
.card-heading strong { color: #243653; font-size: 15px; }
.card-heading span { color: #98a2b3; font-size: 12px; }
.progress-list { display: grid; }
.progress-item { display: grid; grid-template-columns: 14px minmax(0, 1fr) auto; align-items: center; gap: 12px; padding: 15px 2px; border-bottom: 1px solid #edf0f4; }
.progress-item:last-child { border-bottom: 0; }
.progress-dot { width: 8px; height: 8px; border: 2px solid #8ab8ef; border-radius: 50%; background: #e9f3ff; }
.progress-item strong { color: #344054; font-size: 13px; }
.progress-item p { margin: 4px 0 0; color: #98a2b3; font-size: 11px; }
.boundary-content { display: grid; gap: 16px; }
.boundary-line { display: flex; justify-content: space-between; gap: 14px; padding-bottom: 13px; border-bottom: 1px solid #edf0f4; font-size: 13px; }
.boundary-line span { color: #667085; }.boundary-line strong { color: #344054; font-weight: 600; text-align: right; }
@media (max-width: 1180px) { .summary-grid { grid-template-columns: repeat(2, 1fr); } .content-grid { grid-template-columns: 1fr; } }
@media (max-width: 680px) { .summary-grid { grid-template-columns: 1fr; } .welcome-banner { flex-direction: column; } }
</style>
