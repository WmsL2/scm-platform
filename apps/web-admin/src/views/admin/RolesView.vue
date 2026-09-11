<script setup lang="ts">
import { onMounted, reactive, ref } from "vue"
import { ElMessage, ElMessageBox } from "element-plus"
import { accountApi } from "../../api/account"
import { HttpError } from "../../shared/http"
import { useAuthStore } from "../../stores/auth"
import type { AccountRole, Permission } from "../../types/account"
const auth = useAuthStore()
const roles = ref<AccountRole[]>([])
const permissions = ref<Permission[]>([])
const edited = ref<AccountRole | null>(null)
const permissionIds = ref<string[]>([])
const openingRoleId = ref<string | null>(null)
const permissionSubmitting = ref(false)
const createVisible = ref(false)
const createSubmitting = ref(false)
const deletingRoleId = ref<string | null>(null)
const createForm = reactive({ role_code: "", role_name: "" })
const roleCodePattern = /^[a-z][a-z0-9_]{0,63}$/

async function load() {
  roles.value = await accountApi.roles()
}

async function open(row: AccountRole) {
  if (openingRoleId.value || permissionSubmitting.value) return
  openingRoleId.value = row.id
  try {
    permissions.value = await accountApi.permissions()
    edited.value = row
    permissionIds.value = [...row.permission_ids]
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "加载权限失败")
  } finally {
    openingRoleId.value = null
  }
}

function openCreate() {
  createForm.role_code = ""
  createForm.role_name = ""
  createVisible.value = true
}

async function create() {
  const roleCode = createForm.role_code.trim()
  const roleName = createForm.role_name.trim()
  if (!roleCodePattern.test(roleCode)) {
    ElMessage.warning("角色编码必须以小写英文开头，只能包含小写英文、数字和下划线")
    return
  }
  if (!roleName) {
    ElMessage.warning("请输入角色名称")
    return
  }
  createSubmitting.value = true
  try {
    const role = await accountApi.createRole({ role_code: roleCode, role_name: roleName })
    createVisible.value = false
    await load()
    ElMessage.success("角色已创建，请继续配置权限")
    if (
      auth.hasPermission("system:role:permission:update")
      && auth.hasPermission("system:permission:list")
    ) {
      await open(role)
    }
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "创建失败")
  } finally {
    createSubmitting.value = false
  }
}

async function remove(row: AccountRole) {
  if (deletingRoleId.value || row.is_builtin) return
  try {
    await ElMessageBox.confirm(
      `删除角色“${row.role_name}”后将不能继续分配或使用该角色。已分配给用户的角色不能删除。`,
      "确认删除角色",
      { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" },
    )
  } catch {
    return
  }
  deletingRoleId.value = row.id
  try {
    await accountApi.deleteRole(row.id)
    await load()
    ElMessage.success("角色已删除")
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "删除角色失败")
  } finally {
    deletingRoleId.value = null
  }
}

async function save() {
  if (!edited.value || permissionSubmitting.value) return
  const role = edited.value
  permissionSubmitting.value = true
  try {
    await accountApi.setRolePermissions(role.id, permissionIds.value)
    if (auth.currentUser?.roles.includes(role.role_code)) {
      await auth.refreshCurrentUser()
    }
    await load()
    edited.value = null
    ElMessage.success("权限已保存")
  } catch (error) {
    ElMessage.error(error instanceof HttpError ? error.response.message : "保存失败")
  } finally {
    permissionSubmitting.value = false
  }
}

onMounted(load)
</script>
<template>
  <el-card>
    <div class="page-header">
      <h2>角色权限</h2>
      <el-button v-if="auth.hasPermission('system:role:create')" type="primary" @click="openCreate">新增角色</el-button>
    </div>
    <el-table :data="roles">
      <el-table-column prop="role_code" label="角色编码" />
      <el-table-column prop="role_name" label="角色名称" />
      <el-table-column label="操作" width="220">
        <template #default="{ row }">
          <el-button v-if="auth.hasPermission('system:role:permission:update')" text type="primary" :loading="openingRoleId === row.id" :disabled="Boolean(openingRoleId) || permissionSubmitting" @click="open(row)">配置权限</el-button>
          <el-button v-if="!row.is_builtin && auth.hasPermission('system:role:delete')" text type="danger" :loading="deletingRoleId === row.id" :disabled="Boolean(deletingRoleId)" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="createVisible" title="新增角色" width="480px" :close-on-click-modal="!createSubmitting">
    <el-form label-position="top">
      <el-form-item label="角色编码" required>
        <el-input v-model="createForm.role_code" maxlength="64" placeholder="例如：pricing_operator" />
        <div class="field-tip">创建后不可修改；以小写英文开头，仅可使用小写英文、数字和下划线。</div>
      </el-form-item>
      <el-form-item label="角色名称" required>
        <el-input v-model="createForm.role_name" maxlength="128" placeholder="例如：报价管理员" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="createSubmitting" @click="createVisible = false">取消</el-button>
      <el-button type="primary" :loading="createSubmitting" @click="create">创建并配置权限</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="edited" title="配置权限" :close-on-click-modal="!permissionSubmitting" :close-on-press-escape="!permissionSubmitting" :show-close="!permissionSubmitting">
    <el-checkbox-group v-model="permissionIds" :disabled="permissionSubmitting">
      <el-checkbox v-for="item in permissions" :key="item.id" :value="item.id">{{ item.permission_name }}</el-checkbox>
    </el-checkbox-group>
    <template #footer>
      <el-button :disabled="permissionSubmitting" @click="edited = null">取消</el-button>
      <el-button type="primary" :loading="permissionSubmitting" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.page-header h2 { margin: 0; }
.field-tip { margin-top: 6px; color: var(--el-text-color-secondary); font-size: 12px; line-height: 1.5; }
</style>
