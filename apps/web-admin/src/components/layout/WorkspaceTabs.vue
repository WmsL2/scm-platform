<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import type { TabPaneName } from "element-plus"
import Sortable, { type MoveEvent, type SortableEvent } from "sortablejs"

import { useWorkspaceStore } from "../../stores/workspace"

const route = useRoute()
const router = useRouter()
const workspace = useWorkspaceStore()
const tabsRoot = ref<HTMLElement>()
let sortable: Sortable | undefined
let placeholderItem: HTMLElement | undefined

const activePath = computed({
  get: () => route.fullPath,
  set: (path: string) => { void router.push(path) },
})

function closeTab(target: TabPaneName): void {
  const path = String(target)
  const fallback = workspace.close(path)
  if (path === route.fullPath) void router.push(fallback)
}

function applySortedOrder(event: SortableEvent): void {
  clearPlaceholder(event.item)
  const oldIndex = event.oldDraggableIndex
  const newIndex = event.newDraggableIndex
  if (oldIndex === undefined || newIndex === undefined) return
  workspace.moveByIndex(oldIndex, newIndex)
}

function showPlaceholder(event: SortableEvent): void {
  placeholderItem = event.item
  applyPlaceholderStyle(event.item)
}

function maintainPlaceholder(event: MoveEvent): void {
  placeholderItem = event.dragged
  applyPlaceholderStyle(event.dragged)
}

function applyPlaceholderStyle(item: HTMLElement): void {
  item.classList.add("workspace-tab-placeholder")
  item.style.setProperty("color", "transparent", "important")
  item.style.setProperty("border-color", "#1d4ed8", "important")
  item.style.setProperty("border-style", "dashed", "important")
  item.style.setProperty("background-color", "#7fb7f5", "important")
  item.style.setProperty("box-shadow", "inset 0 0 0 2px rgb(29 78 216 / 38%), 0 0 0 2px rgb(59 130 246 / 14%)", "important")
  item.style.setProperty("opacity", "1", "important")
  item.querySelector<HTMLElement>(".is-icon-close")?.style.setProperty("visibility", "hidden", "important")
}

function clearPlaceholder(item = placeholderItem): void {
  if (!item) return
  item.classList.remove("workspace-tab-placeholder")
  for (const property of ["color", "border-color", "border-style", "background-color", "box-shadow", "opacity"]) {
    item.style.removeProperty(property)
  }
  item.querySelector<HTMLElement>(".is-icon-close")?.style.removeProperty("visibility")
  placeholderItem = undefined
}

async function initializeSortable(): Promise<void> {
  await nextTick()
  const tabNav = tabsRoot.value?.querySelector<HTMLElement>(".el-tabs__nav")
  if (!tabNav) return
  sortable?.destroy()
  sortable = Sortable.create(tabNav, {
    draggable: ".el-tabs__item",
    direction: "horizontal",
    animation: 180,
    forceFallback: true,
    fallbackOnBody: true,
    fallbackTolerance: 4,
    swapThreshold: 0.65,
    invertSwap: true,
    invertedSwapThreshold: 0.65,
    filter: ".is-icon-close",
    preventOnFilter: false,
    ghostClass: "workspace-tab-sortable-ghost",
    chosenClass: "workspace-tab-chosen",
    dragClass: "workspace-tab-dragging",
    fallbackClass: "workspace-tab-fallback",
    onStart: showPlaceholder,
    onMove: maintainPlaceholder,
    onEnd: applySortedOrder,
  })
}

onMounted(() => { void initializeSortable() })
onBeforeUnmount(() => {
  clearPlaceholder()
  sortable?.destroy()
})
</script>

<template>
  <div ref="tabsRoot" class="workspace-tabs">
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
:deep(.el-tabs__item) { height: 34px; border: 1px solid var(--border) !important; border-radius: 7px 7px 0 0; color: #667085; background: #f8fafc; cursor: grab; user-select: none; }
:deep(.el-tabs__item.is-active) { color: var(--brand-700); border-bottom-color: #fff !important; background: #fff; font-weight: 600; }
:deep(.el-tabs__item:active) { cursor: grabbing; }
:global(.el-tabs__item.workspace-tab-chosen) { border-color: #3b82f6 !important; background-color: #dbeafe !important; box-shadow: 0 4px 12px rgb(37 99 235 / 24%) !important; cursor: grabbing !important; }
:global(.el-tabs__item.workspace-tab-placeholder),
:global(.el-tabs__item.is-active.workspace-tab-placeholder) { color: transparent !important; border-color: #1d4ed8 !important; border-style: dashed !important; background-color: #7fb7f5 !important; box-shadow: inset 0 0 0 2px rgb(29 78 216 / 38%), 0 0 0 2px rgb(59 130 246 / 14%) !important; opacity: 1 !important; }
:global(.el-tabs__item.workspace-tab-placeholder .is-icon-close) { visibility: hidden !important; }
:global(.workspace-tab-fallback) { z-index: 3000 !important; opacity: .58 !important; border: 1px solid var(--brand-600, #409eff) !important; border-radius: 7px 7px 0 0; background: #fff !important; box-shadow: 0 8px 20px rgb(15 23 42 / 18%); cursor: grabbing !important; }
</style>
