import { describe, expect, it } from "vitest"

import type { ProductCategoryFilterOption } from "../../types/catalog"
import {
  derivedLevel1Keys,
  derivedLevel2Keys,
  updateExplicitSelection,
  visibleSelection,
} from "./categoryMultiSelect"

const camera: ProductCategoryFilterOption = {
  selection_key: "LEVEL3:camera", label: "数码 / 摄影 / 相机", level: "LEVEL3",
  level1_selection_key: "LEVEL1:camera", level2_selection_key: "LEVEL2:camera",
  level1_label: "数码", level2_label: "数码 / 摄影",
}
const printer: ProductCategoryFilterOption = {
  selection_key: "LEVEL3:printer", label: "办公 / 办公设备 / 打印机", level: "LEVEL3",
  level1_selection_key: "LEVEL1:printer", level2_selection_key: "LEVEL2:printer",
  level1_label: "办公", level2_label: "办公 / 办公设备",
}

describe("product category multi-select", () => {
  it("derives parent selection keys from direct level-3 choices", () => {
    const options = new Map([[camera.selection_key, camera], [printer.selection_key, printer]])

    expect(derivedLevel2Keys(options, [camera.selection_key, printer.selection_key])).toEqual([
      "LEVEL2:camera", "LEVEL2:printer",
    ])
    expect(derivedLevel1Keys(options, [], [camera.selection_key, printer.selection_key])).toEqual([
      "LEVEL1:camera", "LEVEL1:printer",
    ])
  })

  it("keeps a child-derived parent visible when the user tries to remove it", () => {
    const derived = ["LEVEL1:camera"]
    const visible = visibleSelection([], derived)

    expect(updateExplicitSelection([], visible, [], derived)).toEqual([])
    expect(visibleSelection([], derived)).toEqual(["LEVEL1:camera"])
  })
})
