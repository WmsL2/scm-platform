<script setup lang="ts">
import { onMounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { accountApi } from "../../api/account"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type { AccountRole, AccountUser } from "../../types/account"
const auth=useAuthStore(),users=ref<AccountUser[]>([]),roles=ref<AccountRole[]>([]),edited=ref<AccountUser|null>(null),roleIds=ref<string[]>([]),saving=ref(false)
async function load(){users.value=(await accountApi.users()).items}
async function open(row:AccountUser){try{roles.value=await accountApi.roles();edited.value=row;roleIds.value=[...row.role_ids]}catch(e){ElMessage.error(e instanceof HttpError?e.response.message:"加载角色失败")}}
async function save(){if(!edited.value)return;saving.value=true;try{await accountApi.setUserRoles(edited.value.id,roleIds.value);ElMessage.success("角色已更新");edited.value=null;await load()}catch(e){ElMessage.error(e instanceof HttpError?e.response.message:"保存失败")}finally{saving.value=false}}
onMounted(load)
</script>
<template><el-card><h2>用户管理</h2><el-table :data="users"><el-table-column prop="username" label="用户名"/><el-table-column prop="user_status" label="状态"/><el-table-column label="角色"><template #default="{row}">{{row.role_ids.join(', ')||'—'}} <el-button v-if="auth.hasPermission('system:user:role:update')" text @click="open(row)">分配角色</el-button></template></el-table-column></el-table><el-dialog v-model="edited" title="分配角色"><el-checkbox-group v-model="roleIds"><el-checkbox v-for="role in roles" :key="role.id" :value="role.id">{{role.role_name}}（{{role.role_code}}）</el-checkbox></el-checkbox-group><template #footer><el-button @click="edited=null">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template></el-dialog></el-card></template>
