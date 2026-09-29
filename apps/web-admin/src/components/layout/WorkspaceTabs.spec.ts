import { describe, expect, it } from "vitest"
import source from "./WorkspaceTabs.vue?raw"

describe("WorkspaceTabs", () => {
  it("keeps a full tab preview horizontally constrained when the pointer leaves the strip", () => {
    expect(source).not.toContain('from "sortablejs"')
    expect(source).toContain('document.addEventListener("pointermove", onDocumentPointerMove, true)')
    expect(source).toContain('document.addEventListener("pointerup", onDocumentPointerUp, true)')
    expect(source).toContain("const maximumLeft")
    expect(source).toContain("const left = Math.min(Math.max(clientX - drag.pointerOffsetX, headerRect.left), maximumLeft)")
    expect(source).toContain("drag.preview.style.top")
    expect(source).toContain("moveTabWithAnimation(drag.item, before)")
    expect(source).toContain("const deltaX = previous.left - next.left")
    expect(source).toContain('tab.style.transition = "transform 180ms ease"')
    expect(source).toContain("workspace.moveByIndex(drag.oldIndex, newIndex)")
    expect(source).toContain("workspace-tab-drag-preview")
    expect(source).toContain("opacity: 1")
    expect(source).toContain('item.style.setProperty("visibility", "hidden", "important")')
    expect(source).toContain('drag.item.style.removeProperty("visibility")')
    expect(source).toContain("radial-gradient(circle at 100% 0")
    expect(source).toContain("radial-gradient(circle at 0 0")
  })
})
