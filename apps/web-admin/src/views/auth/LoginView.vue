<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import { Check, Connection, Lock, User } from "@element-plus/icons-vue"
import { ElMessage, type FormInstance, type FormRules } from "element-plus"

import { accountApi } from "../../api/account"
import { isMockMode } from "../../api/auth"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type { LoginRequest } from "../../types/auth"

type AuthMode = "login" | "register"

interface RegisterForm {
  username: string
  password: string
  confirm: string
}

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loginFormRef = ref<FormInstance>()
const registerFormRef = ref<FormInstance>()
const loginSubmitting = ref(false)
const registerSubmitting = ref(false)
const registrationDone = ref(false)
const appTitle = import.meta.env.VITE_APP_TITLE ?? "众诚智链商品管理平台"

const mode = computed<AuthMode>(() => (route.name === "register" ? "register" : "login"))

const loginForm = reactive<LoginRequest>({
  username: isMockMode ? "admin" : "",
  password: "",
})

const registerForm = reactive<RegisterForm>({
  username: "",
  password: "",
  confirm: "",
})

const loginRules: FormRules<LoginRequest> = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { max: 64, message: "用户名不能超过 64 个字符", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { max: 256, message: "密码不能超过 256 个字符", trigger: "blur" },
  ],
}

const registerRules: FormRules<RegisterForm> = {
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { max: 64, message: "用户名不能超过 64 个字符", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { max: 256, message: "密码不能超过 256 个字符", trigger: "blur" },
  ],
  confirm: [
    { required: true, message: "请再次输入密码", trigger: "blur" },
    {
      validator: (_rule, value: string, callback) => {
        if (value !== registerForm.password) callback(new Error("两次输入的密码不一致"))
        else callback()
      },
      trigger: ["blur", "change"],
    },
  ],
}

const redirectTarget = computed(() => {
  const value = route.query.redirect
  return typeof value === "string" && value.startsWith("/") && !value.startsWith("//")
    ? value
    : "/dashboard"
})

onMounted(() => {
  if (route.query.reason === "expired") {
    ElMessage.warning("登录状态已失效，请重新登录")
  }
})

async function switchMode(target: AuthMode): Promise<void> {
  if (target === mode.value) return
  registrationDone.value = false
  const query = target === "login" && route.query.redirect
    ? { redirect: route.query.redirect }
    : undefined
  await router.replace({ name: target, query })
}

async function submitLogin(): Promise<void> {
  if (!loginFormRef.value || !(await loginFormRef.value.validate().catch(() => false))) return
  loginSubmitting.value = true
  try {
    await auth.login({ ...loginForm })
    ElMessage.success("登录成功")
    await router.replace(redirectTarget.value)
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "登录失败，请稍后重试")
  } finally {
    loginSubmitting.value = false
  }
}

async function submitRegister(): Promise<void> {
  if (
    !registerFormRef.value
    || !(await registerFormRef.value.validate().catch(() => false))
  ) return

  registerSubmitting.value = true
  try {
    await accountApi.register(registerForm.username.trim(), registerForm.password)
    registrationDone.value = true
    ElMessage.success("注册申请已提交")
  } catch (error) {
    const code = (error as { response?: { code?: string } }).response?.code
    ElMessage.error(
      code === "ACCOUNT_USERNAME_EXISTS" ? "该用户名已存在或已被使用。" : "注册提交失败",
    )
  } finally {
    registerSubmitting.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="brand-panel">
      <div class="brand-content">
        <div class="brand-mark">ZC</div>
        <p class="brand-eyebrow">ZHONGCHENG SMART SUPPLY CHAIN</p>
        <h1>让商品、供应商与报价<br>在一套系统里协同</h1>
        <p class="brand-description">
          面向企业采购与商品管理场景的统一工作平台，沉淀可信数据，连接业务流程。
        </p>
        <div class="brand-features">
          <div><el-icon><Check /></el-icon><span>统一商品主数据</span></div>
          <div><el-icon><Check /></el-icon><span>供应商全生命周期管理</span></div>
          <div><el-icon><Check /></el-icon><span>可追溯的权限与操作记录</span></div>
        </div>
      </div>
      <div class="brand-glow brand-glow-one" />
      <div class="brand-glow brand-glow-two" />
    </section>

    <section class="login-panel">
      <div class="login-card">
        <div class="mobile-brand">
          <span class="brand-mark small">ZC</span>
          <strong>{{ appTitle }}</strong>
        </div>

        <div class="auth-tabs" role="tablist" aria-label="账号入口">
          <button
            type="button"
            role="tab"
            :aria-selected="mode === 'login'"
            :class="{ active: mode === 'login' }"
            @click="switchMode('login')"
          >
            登录
          </button>
          <button
            type="button"
            role="tab"
            :aria-selected="mode === 'register'"
            :class="{ active: mode === 'register' }"
            @click="switchMode('register')"
          >
            注册
          </button>
        </div>

        <div class="login-heading">
          <p class="welcome">{{ mode === "login" ? "欢迎回来" : "创建企业账号" }}</p>
          <h2>{{ mode === "login" ? "登录管理平台" : "申请注册账号" }}</h2>
          <p>
            {{
              mode === "login"
                ? "请输入账号信息以继续访问企业工作台"
                : "提交申请后，账号将由管理员审核并开放"
            }}
          </p>
        </div>

        <el-alert
          v-if="mode === 'login' && isMockMode"
          class="mock-alert"
          title="当前为本地 Mock 模式"
          type="warning"
          :closable="false"
          show-icon
        >
          <template #default>演示账号见前端开发文档；本模式不会连接后端数据库。</template>
        </el-alert>

        <el-form
          v-if="mode === 'login'"
          ref="loginFormRef"
          :model="loginForm"
          :rules="loginRules"
          label-position="top"
          size="large"
          @keyup.enter="submitLogin"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="loginForm.username"
              :prefix-icon="User"
              autocomplete="username"
              placeholder="请输入用户名"
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="loginForm.password"
              :prefix-icon="Lock"
              type="password"
              autocomplete="current-password"
              placeholder="请输入密码"
              show-password
            />
          </el-form-item>
          <el-button
            class="submit-button"
            type="primary"
            :loading="loginSubmitting"
            @click="submitLogin"
          >
            登录
          </el-button>
        </el-form>

        <el-alert
          v-else-if="registrationDone"
          class="registration-success"
          title="注册申请已提交"
          description="账号正在等待管理员审批，审批通过后即可登录。"
          type="success"
          :closable="false"
          show-icon
        >
          <template #default>
            <el-button type="primary" @click="switchMode('login')">返回登录</el-button>
          </template>
        </el-alert>

        <el-form
          v-else
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          label-position="top"
          size="large"
          @keyup.enter="submitRegister"
        >
          <el-form-item label="用户名" prop="username">
            <el-input
              v-model="registerForm.username"
              :prefix-icon="User"
              autocomplete="username"
              placeholder="请输入用户名"
            />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input
              v-model="registerForm.password"
              :prefix-icon="Lock"
              type="password"
              autocomplete="new-password"
              placeholder="请输入密码"
              show-password
            />
          </el-form-item>
          <el-form-item label="确认密码" prop="confirm">
            <el-input
              v-model="registerForm.confirm"
              :prefix-icon="Lock"
              type="password"
              autocomplete="new-password"
              placeholder="请再次输入密码"
              show-password
            />
          </el-form-item>
          <el-button
            class="submit-button"
            type="primary"
            :loading="registerSubmitting"
            @click="submitRegister"
          >
            提交注册申请
          </el-button>
        </el-form>

        <div class="security-note">
          <el-icon><Connection /></el-icon>
          <span>{{ mode === "login" ? "登录信息" : "注册信息" }}通过统一认证接口安全传输</span>
        </div>
      </div>
      <footer>© 2026 众诚智链 · 企业商品管理平台</footer>
    </section>
  </main>
</template>

<style scoped>
.login-page { min-height: 100vh; display: grid; grid-template-columns: minmax(440px, 1.12fr) minmax(480px, .88fr); background: #fff; }
.brand-panel { position: relative; display: flex; align-items: center; overflow: hidden; padding: 80px clamp(48px, 7vw, 110px); color: #fff; background: linear-gradient(145deg, #071b3c 0%, #0b3472 52%, #1261bb 100%); }
.brand-content { position: relative; z-index: 2; max-width: 620px; }
.brand-mark { display: grid; width: 58px; height: 58px; place-items: center; border: 1px solid rgba(255,255,255,.34); border-radius: 16px; color: white; font-weight: 800; letter-spacing: .06em; background: rgba(255,255,255,.13); box-shadow: inset 0 1px rgba(255,255,255,.22); backdrop-filter: blur(12px); }
.brand-mark.small { width: 40px; height: 40px; flex: none; border-radius: 11px; background: var(--brand-700); }
.brand-eyebrow { margin: 30px 0 14px; color: #91c4ff; font-size: 12px; font-weight: 700; letter-spacing: .18em; }
.brand-panel h1 { margin: 0; font-size: clamp(38px, 4vw, 58px); line-height: 1.22; letter-spacing: -.04em; }
.brand-description { max-width: 540px; margin: 28px 0 36px; color: #c9dcf5; font-size: 17px; line-height: 1.9; }
.brand-features { display: grid; gap: 16px; color: #e9f3ff; }
.brand-features div { display: flex; align-items: center; gap: 12px; }
.brand-features .el-icon { width: 24px; height: 24px; border-radius: 50%; color: #8dd3ff; background: rgba(109,194,255,.14); }
.brand-glow { position: absolute; border-radius: 50%; filter: blur(2px); }
.brand-glow-one { right: -150px; top: -140px; width: 420px; height: 420px; background: rgba(76, 180, 255, .13); }
.brand-glow-two { left: -140px; bottom: -200px; width: 460px; height: 460px; background: rgba(37, 111, 231, .24); }
.login-panel { display: flex; min-height: 100vh; box-sizing: border-box; flex-direction: column; align-items: center; justify-content: flex-start; overflow-y: auto; padding: 64px 48px 36px; background: radial-gradient(circle at 85% 10%, #edf5ff 0, transparent 28%), #fff; }
.login-card { width: min(100%, 430px); }
.mobile-brand { display: none; align-items: center; gap: 12px; margin-bottom: 36px; }
.auth-tabs { display: grid; grid-template-columns: repeat(2, 1fr); margin-bottom: 30px; padding: 4px; border-radius: 11px; background: #f2f5f9; }
.auth-tabs button { position: relative; height: 44px; border: 0; border-radius: 8px; color: #667085; font: inherit; font-weight: 650; background: transparent; cursor: pointer; transition: color .2s, background-color .2s, box-shadow .2s; }
.auth-tabs button.active { color: var(--brand-700); background: #fff; box-shadow: 0 2px 10px rgba(15, 48, 91, .1); }
.auth-tabs button:focus-visible { outline: 3px solid rgba(29,103,207,.2); outline-offset: 1px; }
.login-heading { margin-bottom: 28px; }
.welcome { margin: 0 0 8px; color: var(--brand-600); font-size: 14px; font-weight: 700; }
.login-heading h2 { margin: 0 0 12px; color: #14213d; font-size: 34px; letter-spacing: -.03em; }
.login-heading > p:last-child { margin: 0; color: var(--text-secondary); line-height: 1.7; }
.mock-alert { margin-bottom: 24px; border-radius: 10px; }
.submit-button { width: 100%; height: 48px; margin-top: 8px; border: 0; border-radius: 9px; font-weight: 700; background: linear-gradient(100deg, var(--brand-700), var(--brand-600)); box-shadow: 0 8px 20px rgba(29,103,207,.22); }
.registration-success { padding: 20px; border-radius: 10px; }
.registration-success .el-button { margin-top: 18px; }
.security-note { display: flex; align-items: center; justify-content: center; gap: 8px; margin-top: 24px; color: #98a2b3; font-size: 13px; }
footer { margin-top: 54px; color: #98a2b3; font-size: 12px; }
:deep(.el-form-item__label) { color: #344054; font-weight: 600; }
:deep(.el-input__wrapper) { min-height: 46px; border-radius: 9px; box-shadow: 0 0 0 1px #d8dee8 inset; }
:deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 1px var(--brand-600) inset, 0 0 0 3px rgba(29,103,207,.1); }
@media (max-width: 920px) { .login-page { grid-template-columns: 1fr; } .brand-panel { display: none; } .login-panel { padding: 32px 22px; } .mobile-brand { display: flex; } }
</style>
