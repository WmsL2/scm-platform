<script setup lang="ts">
import { computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import type { TabPaneName } from "element-plus"

import { useWorkspaceStore } from "../../stores/workspace"

const route = useRoute()
const router = useRouter()
const workspace = useWorkspaceStore()

const activePath = computed({
  get: () => route.fullPath,
  set: (path: string) => { void router.push(path) },
})

function closeTab(target: TabPaneName): void {
  const path = String(target)
  const fallback = workspace.close(path)
  if (path === route.fullPath) void router.push(fallback)
}
</script>

<template>
  <div class="workspace-tabs">
    <el-tabs v-model="activePath" type="card" @tab-remove="closeTab">
      <el-tab-pane
        v-for="tab in workspace.tabs"
        :key="tab.path"
        :label="tab.title"
        :name="tab.path"
        :closable="tab.closable"
      />
    </el-tabs>
  </div>
</template>

<style scoped>
.workspace-tabs { height: 42px; padding: 7px 18px 0; border-bottom: 1px solid var(--border); background: #fff; }
:deep(.el-tabs__header) { margin: 0; border-bottom: 0; }
:deep(.el-tabs__nav) { border: 0 !important; gap: 6px; }
:deep(.el-tabs__item) { height: 34px; border: 1px solid var(--border) !important; border-radius: 7px 7px 0 0; color: #667085; background: #f8fafc; }
:deep(.el-tabs__item.is-active) { color: var(--brand-700); border-bottom-color: #fff !important; background: #fff; font-weight: 600; }
</style>
