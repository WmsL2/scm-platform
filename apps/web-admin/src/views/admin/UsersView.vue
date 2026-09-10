<script setup lang="ts">
import { onMounted, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { accountApi } from "../../api/account"
import { HttpError } from "../../shared/http"
import { userStatusLabel, userStatusTagType } from "../../shared/account/user-status"
import { useAuthStore } from "../../stores/auth"
import type { AccountRole, AccountUser } from "../../types/account"
const auth=useAuthStore(),users=ref<AccountUser[]>([]),roles=ref<AccountRole[]>([]),edited=ref<AccountUser|null>(null),roleIds=ref<string[]>([]),saving=ref(false),deletingUserId=ref<string|null>(null)
async function load(){users.value=(await accountApi.users()).items}
async function open(row:AccountUser){try{roles.value=await accountApi.roles();edited.value=row;roleIds.value=[...row.role_ids]}catch(e){ElMessage.error(e instanceof HttpError?e.response.message:"加载角色失败")}}
async function save(){if(!edited.value)return;saving.value=true;try{await accountApi.setUserRoles(edited.value.id,roleIds.value);ElMessage.success("角色已更新");edited.value=null;await load()}catch(e){ElMessage.error(e instanceof HttpError?e.response.message:"保存失败")}finally{saving.value=false}}
async function deleteUser(row:AccountUser){try{await ElMessageBox.confirm(`确认删除用户“${row.username}”吗？删除后该用户将无法登录，并从正常用户列表中移除，数据库记录仍会保留。`,"确认删除用户",{confirmButtonText:"删除",cancelButtonText:"取消",type:"warning"});deletingUserId.value=row.id;await accountApi.deleteUser(row.id);ElMessage.success("用户已删除");await load()}catch(e){if(e!=="cancel"&&e!=="close")ElMessage.error(e instanceof HttpError?e.response.message:"删除失败")}finally{deletingUserId.value=null}}
onMounted(load)
</script>
<template><el-card><h2>用户管理</h2><el-table :data="users"><el-table-column prop="username" label="用户名"/><el-table-column label="状态"><template #default="{row}"><el-tag :type="userStatusTagType(row.user_status)" effect="plain">{{ userStatusLabel(row.user_status) }}</el-tag></template></el-table-column><el-table-column label="所属角色" min-width="180"><template #default="{row}"><template v-if="row.role_names.length"><el-tag v-for="roleName in row.role_names" :key="roleName" class="role-tag" effect="plain">{{ roleName }}</el-tag></template><span v-else class="unassigned-role">未分配角色</span></template></el-table-column><el-table-column label="操作" width="180"><template #default="{row}"><el-button v-if="row.user_status === 'ENABLED' && auth.hasPermission('system:user:role:update')" text type="primary" @click="open(row)">分配角色</el-button><el-button v-if="auth.hasPermission('system:user:delete') && row.id !== auth.currentUser?.user_id" text type="danger" :loading="deletingUserId === row.id" @click="deleteUser(row)">删除</el-button></template></el-table-column></el-table><el-dialog v-model="edited" title="分配角色"><el-checkbox-group v-model="roleIds"><el-checkbox v-for="role in roles" :key="role.id" :value="role.id">{{ role.role_name }}</el-checkbox></el-checkbox-group><template #footer><el-button @click="edited=null">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存</el-button></template></el-dialog></el-card></template>

<style scoped>
.role-tag { margin: 0 6px 6px 0; }
.unassigned-role { color: var(--text-secondary); }
</style>
