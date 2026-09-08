<script setup lang="ts">
import { onMounted, ref } from "vue"
import { ElMessage } from "element-plus"
import { accountApi } from "../../api/account"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type { AccountRole, Permission } from "../../types/account"
const auth=useAuthStore(),roles=ref<AccountRole[]>([]),permissions=ref<Permission[]>([]),edited=ref<AccountRole|null>(null),permissionIds=ref<string[]>([])
async function load(){roles.value=await accountApi.roles()};async function open(row:AccountRole){permissions.value=await accountApi.permissions();edited.value=row;permissionIds.value=[...row.permission_ids]};async function save(){if(!edited.value)return;try{await accountApi.setRolePermissions(edited.value.id,permissionIds.value);edited.value=null;await load()}catch(e){ElMessage.error(e instanceof HttpError?e.response.message:"保存失败")}};onMounted(load)
</script>
<template><el-card><h2>角色权限</h2><el-table :data="roles"><el-table-column prop="role_code" label="角色编码"/><el-table-column prop="role_name" label="角色名称"/><el-table-column label="操作" width="140"><template #default="{row}"><el-button v-if="auth.hasPermission('system:role:permission:update')" text type="primary" @click="open(row)">配置权限</el-button></template></el-table-column></el-table><el-dialog v-model="edited" title="配置权限"><el-checkbox-group v-model="permissionIds"><el-checkbox v-for="item in permissions" :key="item.id" :value="item.id">{{ item.permission_name }}</el-checkbox></el-checkbox-group><template #footer><el-button @click="edited=null">取消</el-button><el-button type="primary" @click="save">保存</el-button></template></el-dialog></el-card></template>
