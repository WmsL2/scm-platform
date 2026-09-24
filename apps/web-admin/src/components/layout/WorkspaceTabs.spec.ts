import { describe, expect, it } from "vitest"
import source from "./WorkspaceTabs.vue?raw"

describe("WorkspaceTabs", () => {
  it("uses horizontal fallback sorting without native forbidden cursors", () => {
    expect(source).toContain('from "sortablejs"')
    expect(source).toContain('draggable: ".el-tabs__item"')
    expect(source).toContain('direction: "horizontal"')
    expect(source).toContain("forceFallback: true")
    expect(source).toContain("invertSwap: true")
    expect(source).toContain('item.classList.add("workspace-tab-placeholder")')
    expect(source).toContain("item.style.setProperty")
    expect(source).toContain("onMove: maintainPlaceholder")
    expect(source).not.toContain("onUnchoose:")
    expect(source).toContain('ghostClass: "workspace-tab-sortable-ghost"')
    expect(source).not.toContain('ghostClass: "workspace-tab-placeholder"')
    expect(source).toContain("border-style: dashed")
    expect(source).toContain("background-color: #7fb7f5")
    expect(source).toContain(".el-tabs__item.is-active.workspace-tab-placeholder")
    expect(source).toContain("opacity: .58")
    expect(source).toContain("workspace.moveByIndex(oldIndex, newIndex)")
  })
})
