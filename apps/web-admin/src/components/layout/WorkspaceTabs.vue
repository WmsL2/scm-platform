<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue"
import { useRoute, useRouter } from "vue-router"
import type { TabPaneName } from "element-plus"

import { useWorkspaceStore } from "../../stores/workspace"

interface TabDrag {
  item: HTMLElement
  pointerId: number
  oldIndex: number
  pointerOffsetX: number
  preview: HTMLElement
}

const route = useRoute()
const router = useRouter()
const workspace = useWorkspaceStore()
const tabsRoot = ref<HTMLElement>()
let tabNav: HTMLElement | undefined
let pendingDrag: { item: HTMLElement; pointerId: number; startX: number; startY: number } | undefined
let activeDrag: TabDrag | undefined
let suppressNextTabClick = false

const activePath = computed({
  get: () => route.fullPath,
  set: (path: string) => { void router.push(path) },
})

function closeTab(target: TabPaneName): void {
  const path = String(target)
  const fallback = workspace.close(path)
  if (path === route.fullPath) void router.push(fallback)
}

function getTabItems(): HTMLElement[] {
  if (!tabNav) return []
  return Array.from(tabNav.children).filter(
    (element): element is HTMLElement => element instanceof HTMLElement && element.classList.contains("el-tabs__item"),
  )
}

function beginTabDrag(item: HTMLElement, pointerId: number, clientX: number): void {
  const header = tabsRoot.value?.querySelector<HTMLElement>(".el-tabs__header")
  if (!header || !tabNav) return

  const itemRect = item.getBoundingClientRect()
  const preview = item.cloneNode(true) as HTMLElement
  preview.classList.remove("is-active")
  preview.classList.add("workspace-tab-drag-preview")
  preview.style.width = `${itemRect.width}px`
  preview.style.height = `${itemRect.height}px`
  document.body.appendChild(preview)

  activeDrag = {
    item,
    pointerId,
    oldIndex: getTabItems().indexOf(item),
    pointerOffsetX: Math.min(Math.max(clientX - itemRect.left, 0), itemRect.width),
    preview,
  }
  item.classList.add("workspace-tab-placeholder")
  item.style.setProperty("visibility", "hidden", "important")
  tabsRoot.value?.classList.add("workspace-tabs--dragging")
  updateTabDrag(clientX)
}

function updateTabDrag(clientX: number): void {
  const drag = activeDrag
  const header = tabsRoot.value?.querySelector<HTMLElement>(".el-tabs__header")
  if (!drag || !header || !tabNav) return

  const headerRect = header.getBoundingClientRect()
  const previewWidth = drag.preview.getBoundingClientRect().width
  const maximumLeft = Math.max(headerRect.left, headerRect.right - previewWidth)
  const left = Math.min(Math.max(clientX - drag.pointerOffsetX, headerRect.left), maximumLeft)

  // The preview stays in the tab row even if the pointer leaves it vertically.
  drag.preview.style.left = `${left}px`
  drag.preview.style.top = `${headerRect.top + (headerRect.height - drag.preview.offsetHeight) / 2}px`

  const otherTabs = getTabItems().filter((item) => item !== drag.item)
  const before = otherTabs.find((item) => {
    const rect = item.getBoundingClientRect()
    return clientX < rect.left + rect.width / 2
  })
  if (before !== drag.item.nextElementSibling) moveTabWithAnimation(drag.item, before)
}

function moveTabWithAnimation(item: HTMLElement, before: HTMLElement | undefined): void {
  if (!tabNav) return
  const previousPositions = new Map(
    getTabItems()
      .filter((tab) => tab !== item)
      .map((tab) => [tab, tab.getBoundingClientRect()] as const),
  )
  tabNav.insertBefore(item, before ?? null)

  for (const [tab, previous] of previousPositions) {
    const next = tab.getBoundingClientRect()
    const deltaX = previous.left - next.left
    if (deltaX === 0) continue
    tab.style.transition = "none"
    tab.style.transform = `translateX(${deltaX}px)`
    void tab.offsetWidth
    window.requestAnimationFrame(() => {
      tab.style.transition = "transform 180ms ease"
      tab.style.transform = ""
    })
  }
}

function finishTabDrag(commit: boolean): void {
  const drag = activeDrag
  pendingDrag = undefined
  if (!drag) return

  const newIndex = getTabItems().indexOf(drag.item)
  if (!commit && tabNav) {
    const tabs = getTabItems().filter((item) => item !== drag.item)
    tabNav.insertBefore(drag.item, tabs[drag.oldIndex] ?? null)
  }
  drag.preview.remove()
  drag.item.classList.remove("workspace-tab-placeholder")
  drag.item.style.removeProperty("visibility")
  tabsRoot.value?.classList.remove("workspace-tabs--dragging")
  activeDrag = undefined

  if (commit && drag.oldIndex !== newIndex) workspace.moveByIndex(drag.oldIndex, newIndex)
  if (commit) suppressNextTabClick = true
}

function onTabPointerDown(event: PointerEvent): void {
  if (event.button !== 0) return
  const target = event.target
  if (!(target instanceof Element) || target.closest(".is-icon-close")) return
  const item = target.closest<HTMLElement>(".el-tabs__item")
  if (!item || !tabNav?.contains(item)) return
  pendingDrag = { item, pointerId: event.pointerId, startX: event.clientX, startY: event.clientY }
}

function onDocumentPointerMove(event: PointerEvent): void {
  if (pendingDrag && !activeDrag && event.pointerId === pendingDrag.pointerId) {
    if (Math.max(Math.abs(event.clientX - pendingDrag.startX), Math.abs(event.clientY - pendingDrag.startY)) < 4) return
    beginTabDrag(pendingDrag.item, event.pointerId, pendingDrag.startX)
  }
  if (!activeDrag || event.pointerId !== activeDrag.pointerId) return
  event.preventDefault()
  updateTabDrag(event.clientX)
}

function onDocumentPointerUp(event: PointerEvent): void {
  if (activeDrag && event.pointerId === activeDrag.pointerId) finishTabDrag(true)
  else if (pendingDrag?.pointerId === event.pointerId) pendingDrag = undefined
}

function onDocumentPointerCancel(event: PointerEvent): void {
  if (activeDrag && event.pointerId === activeDrag.pointerId) finishTabDrag(false)
  else if (pendingDrag?.pointerId === event.pointerId) pendingDrag = undefined
}

function suppressClickAfterDrag(event: MouseEvent): void {
  if (!suppressNextTabClick) return
  suppressNextTabClick = false
  event.preventDefault()
  event.stopPropagation()
}

async function initializeTabNav(): Promise<void> {
  await nextTick()
  tabNav = tabsRoot.value?.querySelector<HTMLElement>(".el-tabs__nav") ?? undefined
}

onMounted(() => {
  document.addEventListener("pointermove", onDocumentPointerMove, true)
  document.addEventListener("pointerup", onDocumentPointerUp, true)
  document.addEventListener("pointercancel", onDocumentPointerCancel, true)
  void initializeTabNav()
})
onBeforeUnmount(() => {
  finishTabDrag(false)
  document.removeEventListener("pointermove", onDocumentPointerMove, true)
  document.removeEventListener("pointerup", onDocumentPointerUp, true)
  document.removeEventListener("pointercancel", onDocumentPointerCancel, true)
})
</script>

<template>
  <div ref="tabsRoot" class="workspace-tabs" @pointerdown="onTabPointerDown" @click.capture="suppressClickAfterDrag">
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
.workspace-tabs { position: relative; height: 42px; overflow: hidden; padding: 7px 18px 0; border-bottom: 1px solid var(--border); background: #fff; }
.workspace-tabs--dragging { user-select: none; }
:deep(.el-tabs__header) { height: 35px; margin: 0; overflow: hidden; border-bottom: 0; }
:deep(.el-tabs__nav-wrap),
:deep(.el-tabs__nav-scroll) { overflow: hidden; }
:deep(.el-tabs__nav) { border: 0 !important; gap: 6px; }
:deep(.el-tabs__item) { height: 34px; border: 1px solid var(--border) !important; border-radius: 7px 7px 0 0; color: #667085; background: #f8fafc; cursor: grab; user-select: none; }
:deep(.el-tabs__item.is-active) { position: relative; z-index: 1; overflow: visible; color: var(--brand-700); border-bottom-color: transparent !important; background: #fff; font-weight: 600; }
:deep(.el-tabs__item.is-active::before),
:deep(.el-tabs__item.is-active::after) { position: absolute; bottom: -1px; width: 9px; height: 9px; content: ""; pointer-events: none; }
:deep(.el-tabs__item.is-active::before) { left: -9px; background: radial-gradient(circle at 100% 0, #fff 0 7px, transparent 7.5px); }
:deep(.el-tabs__item.is-active::after) { right: -9px; background: radial-gradient(circle at 0 0, #fff 0 7px, transparent 7.5px); }
:deep(.el-tabs__item:active) { cursor: grabbing; }
:global(.workspace-tab-drag-preview) { position: fixed; z-index: 3000; box-sizing: border-box; margin: 0; opacity: 1; border: 1px solid var(--brand-600, #409eff) !important; border-radius: 7px 7px 0 0; background: #fff !important; box-shadow: 0 8px 20px rgb(15 23 42 / 18%); cursor: grabbing; pointer-events: none; }
</style>
