<script setup lang="ts">
import { reactive, ref } from "vue"
import { useRouter } from "vue-router"
import { ElMessage } from "element-plus"
import { accountApi } from "../../api/account"
const router = useRouter(); const form = reactive({ username: "", password: "", confirm: "" }); const done = ref(false)
async function submit() { const username = form.username.trim(); if (!username || form.password !== form.confirm) return ElMessage.error("请检查用户名和两次密码"); try { await accountApi.register(username, form.password); done.value = true } catch (error) { const code = (error as { response?: { code?: string } }).response?.code; ElMessage.error(code === "ACCOUNT_USERNAME_EXISTS" ? "该用户名已存在或已被使用。" : "注册提交失败") } }
</script>
<template><main class="register"><el-card><h2>注册账号</h2><el-alert v-if="done" title="注册申请已提交，账号正在等待管理员审批。" type="success" :closable="false"/><el-form v-else @submit.prevent="submit"><el-input v-model="form.username" placeholder="用户名"/><el-input v-model="form.password" type="password" placeholder="密码"/><el-input v-model="form.confirm" type="password" placeholder="确认密码"/><el-button type="primary" @click="submit">提交申请</el-button></el-form><el-button text @click="router.push('/login')">返回登录</el-button></el-card></main></template>
<style scoped>.register{display:grid;min-height:100vh;place-items:center}.el-card{width:380px}.el-input,.el-button{margin-top:12px;width:100%}</style>
