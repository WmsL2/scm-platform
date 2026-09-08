<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import {
  ArrowDown,
  Expand,
  Fold,
  House,
  OfficeBuilding,
  SwitchButton,
  UserFilled,
  Setting,
} from "@element-plus/icons-vue"
import { ElMessage } from "element-plus"

import WorkspaceTabs from "../components/layout/WorkspaceTabs.vue"
import { useAuthStore } from "../stores/auth"
import { useRegistrationStore } from "../stores/registration"
import { useWorkspaceStore } from "../stores/workspace"
import { accountApi } from "../api/account"
import { HttpError } from "../shared/http"

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const registration = useRegistrationStore()
const workspace = useWorkspaceStore()
const collapsed = ref(false)
const appTitle = import.meta.env.VITE_APP_TITLE ?? "众诚智链商品管理平台"
const profileVisible = ref(false)
const passwordVisible = ref(false)
const passwordSubmitting = ref(false)
const passwordForm = reactive({ current_password: "", new_password: "", confirm_new_password: "" })
const hasSystemMenu = computed(() => ["system:user:list", "system:role:list", "system:registration:list"].some((item) => auth.hasPermission(item)))

const sidebarWidth = computed(() => collapsed.value ? "72px" : "232px")
const activeMenu = computed(() => route.path.startsWith("/dashboard") ? "/dashboard" : route.path)
const pageTitle = computed(() => typeof route.meta.title === "string" ? route.meta.title : "工作台")

watch(
  () => route.fullPath,
  () => workspace.openRoute(route),
  { immediate: true },
)

watch(
  () => auth.hasPermission("system:registration:list"),
  (canViewRegistrations) => {
    if (!canViewRegistrations) {
      registration.clear()
      return
    }
    void registration.refreshPendingCount().catch(() => registration.clear())
  },
  { immediate: true },
)

async function handleUserCommand(command: string): Promise<void> {
  if (command === "profile") profileVisible.value = true
  else if (command === "password") passwordVisible.value = true
  else if (command === "logout") { await auth.logout(); workspace.reset(); await router.replace({ name: "login" }) }
}
async function changePassword(): Promise<void> { if (passwordForm.new_password !== passwordForm.confirm_new_password) { ElMessage.error("两次新密码不一致"); return }; passwordSubmitting.value = true; try { await accountApi.changePassword(passwordForm.current_password, passwordForm.new_password); ElMessage.success("密码修改成功，请重新登录"); auth.clearSession(); workspace.reset(); passwordVisible.value = false; await router.replace({ name: "login" }) } catch (error) { ElMessage.error(error instanceof HttpError ? error.response.message : "密码修改失败") } finally { passwordSubmitting.value = false } }
</script>

<template>
  <el-container class="app-shell">
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="logo-area">
        <div class="logo-mark">ZC</div>
        <div v-show="!collapsed" class="logo-copy">
          <strong>众诚智链</strong>
          <span>SCM PLATFORM</span>
        </div>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        :collapse-transition="false"
        router
        class="sidebar-menu"
      >
        <el-menu-item index="/dashboard">
          <el-icon><House /></el-icon>
          <template #title>工作台</template>
        </el-menu-item>
        <el-menu-item v-if="auth.hasPermission('supplier:list')" index="/suppliers">
          <el-icon><OfficeBuilding /></el-icon>
          <template #title>供应商管理</template>
        </el-menu-item>
        <template v-if="hasSystemMenu"><el-menu-item-group title="系统管理"><el-menu-item v-if="auth.hasPermission('system:user:list')" index="/admin/users"><el-icon><Setting /></el-icon><template #title>用户管理</template></el-menu-item><el-menu-item v-if="auth.hasPermission('system:role:list')" index="/admin/roles"><el-icon><Setting /></el-icon><template #title>角色权限</template></el-menu-item><el-menu-item v-if="auth.hasPermission('system:registration:list')" index="/admin/registrations"><el-icon><Setting /></el-icon><template #title><el-badge :value="registration.pendingCount" :hidden="registration.pendingCount === 0" class="registration-badge"><span class="registration-menu-label">注册审批</span></el-badge></template></el-menu-item></el-menu-item-group></template>
      </el-menu>

      <div v-show="!collapsed" class="sidebar-boundary">
        <span>一期建设范围</span>
        <p>业务菜单将在接口和字段冻结后逐步开放</p>
      </div>
      <div class="sidebar-version" :class="{ compact: collapsed }">
        <span v-if="!collapsed">Version 0.1.0</span>
        <span v-else>V1</span>
      </div>
    </el-aside>

    <el-container class="main-shell">
      <el-header class="topbar">
        <div class="topbar-left">
          <el-button class="collapse-button" text @click="collapsed = !collapsed">
            <el-icon :size="20"><Expand v-if="collapsed" /><Fold v-else /></el-icon>
          </el-button>
          <div class="breadcrumb">
            <span>{{ appTitle }}</span>
            <i>/</i>
            <strong>{{ pageTitle }}</strong>
          </div>
        </div>

        <el-dropdown trigger="click" @command="handleUserCommand">
          <button class="user-button" type="button">
            <span class="avatar"><el-icon><UserFilled /></el-icon></span>
            <span class="user-copy">
              <strong>{{ auth.username }}</strong>
              <small>{{ auth.currentUser?.roles[0] ?? "已认证用户" }}</small>
            </span>
            <el-icon class="user-arrow"><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人信息</el-dropdown-item>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" :icon="SwitchButton">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <WorkspaceTabs />

      <el-dialog v-model="profileVisible" title="个人信息"><p>用户名：{{ auth.currentUser?.username }}</p><p>角色：</p><el-tag v-for="role in auth.currentUser?.roles" :key="role" class="tag">{{ role }}</el-tag><span v-if="!auth.currentUser?.roles.length">暂无角色</span><p>权限：</p><div class="permission-list"><el-tag v-for="permission in auth.currentUser?.permissions" :key="permission" class="tag">{{ permission }}</el-tag><span v-if="!auth.currentUser?.permissions.length">暂无权限</span></div></el-dialog>
      <el-dialog v-model="passwordVisible" title="修改密码"><el-input v-model="passwordForm.current_password" type="password" placeholder="当前密码"/><el-input v-model="passwordForm.new_password" type="password" placeholder="新密码"/><el-input v-model="passwordForm.confirm_new_password" type="password" placeholder="确认新密码"/><template #footer><el-button @click="passwordVisible=false">取消</el-button><el-button type="primary" :loading="passwordSubmitting" @click="changePassword">保存</el-button></template></el-dialog>

      <el-main class="main-content">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-shell { min-height: 100vh; background: #f3f6fa; }
.sidebar { position: relative; z-index: 3; display: flex; flex-direction: column; overflow: hidden; color: #d6e3f5; background: linear-gradient(180deg, #071b3b 0%, #0a2b58 100%); box-shadow: 8px 0 28px rgba(13, 35, 68, .08); transition: width .2s ease; }
.logo-area { display: flex; height: 72px; align-items: center; gap: 12px; padding: 0 17px; border-bottom: 1px solid rgba(255,255,255,.08); }
.logo-mark { display: grid; width: 38px; height: 38px; flex: none; place-items: center; border: 1px solid rgba(255,255,255,.28); border-radius: 11px; color: #fff; font-size: 13px; font-weight: 800; letter-spacing: .04em; background: linear-gradient(145deg, #1d72df, #3a8df1); }
.logo-copy { min-width: 150px; display: grid; gap: 2px; }
.logo-copy strong { color: #fff; font-size: 17px; letter-spacing: .04em; }
.logo-copy span { color: #7fa6d3; font-size: 9px; letter-spacing: .16em; }
.sidebar-menu { flex: 1; padding: 16px 10px; border-right: 0; background: transparent; }
.sidebar-menu:not(.el-menu--collapse) { width: 232px; }
:deep(.el-menu-item) { height: 46px; margin-bottom: 6px; border-radius: 8px; color: #b9cbe1; }
:deep(.el-menu-item:hover) { color: #fff; background: rgba(255,255,255,.08); }
:deep(.el-menu-item.is-active) { color: #fff; background: linear-gradient(100deg, rgba(35,116,224,.9), rgba(42,137,239,.78)); box-shadow: 0 8px 20px rgba(0, 75, 178, .22); }
.sidebar-boundary { margin: 0 14px 16px; padding: 14px; border: 1px solid rgba(138,190,255,.12); border-radius: 10px; background: rgba(255,255,255,.04); }
.sidebar-boundary span { color: #9ec8f8; font-size: 12px; font-weight: 700; }
.sidebar-boundary p { margin: 7px 0 0; color: #7896b9; font-size: 11px; line-height: 1.6; }
.sidebar-version { padding: 15px 22px; color: #55779e; font-size: 10px; border-top: 1px solid rgba(255,255,255,.06); }
.sidebar-version.compact { padding-inline: 28px; }
.main-shell { min-width: 0; }
.topbar { display: flex; height: 72px; align-items: center; justify-content: space-between; padding: 0 24px 0 16px; border-bottom: 1px solid var(--border); background: rgba(255,255,255,.96); }
.topbar-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
.collapse-button { width: 38px; height: 38px; color: #475467; border-radius: 8px; }
.breadcrumb { display: flex; align-items: center; gap: 10px; overflow: hidden; color: #98a2b3; font-size: 13px; white-space: nowrap; }
.breadcrumb span { overflow: hidden; text-overflow: ellipsis; }
.breadcrumb i { color: #d0d5dd; font-style: normal; }
.breadcrumb strong { color: #344054; font-weight: 600; }
.user-button { display: flex; align-items: center; gap: 10px; padding: 6px 9px; border: 0; border-radius: 10px; color: var(--text-primary); background: transparent; cursor: pointer; }
.user-button:hover { background: #f3f6fa; }
.avatar { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 10px; color: #fff; background: linear-gradient(145deg, var(--brand-700), #3e8ff1); }
.user-copy { display: grid; min-width: 82px; gap: 1px; text-align: left; }
.user-copy strong { max-width: 120px; overflow: hidden; font-size: 13px; text-overflow: ellipsis; }
.user-copy small { max-width: 120px; overflow: hidden; color: #98a2b3; font-size: 10px; text-overflow: ellipsis; }
.user-arrow { color: #98a2b3; }
.main-content { padding: 22px; background: #f3f6fa; }
.tag { margin: 0 6px 6px 0; }.permission-list { max-height: 180px; overflow: auto; }.el-dialog .el-input { margin-bottom: 12px; }
.registration-menu-label { display: inline-block; line-height: 1; }
.registration-badge :deep(.el-badge__content) { top: 50%; right: -10px; transform: translateY(-50%) translateX(100%); }
.page-enter-active, .page-leave-active { transition: opacity .16s ease, transform .16s ease; }
.page-enter-from { opacity: 0; transform: translateY(4px); }
.page-leave-to { opacity: 0; }
@media (max-width: 720px) { .breadcrumb span, .breadcrumb i, .user-copy { display: none; } .topbar { padding-right: 12px; } .main-content { padding: 14px; } }
</style>
