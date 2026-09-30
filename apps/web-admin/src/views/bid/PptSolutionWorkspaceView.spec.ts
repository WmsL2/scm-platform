import { describe, expect, it } from "vitest"
import source from "./PptSolutionWorkspaceView.vue?raw"

describe("PptSolutionWorkspaceView", () => {
  it("keeps AI recommendation, human confirmation, bundling and PPT generation explicit", () => {
    expect(source).toContain("AI 推荐候选")
    expect(source).toContain("人工已选商品")
    expect(source).toContain("组成套装")
    expect(source).toContain("组套仅用于把多件商品合成一页")
    expect(source).toContain("完成选品")
    expect(source).toContain("formatMoney")
    expect(source).toContain("固定使用系统默认模板")
    expect(source).toContain("生成系统 PPT")
    expect(source).toContain("下载 PPTX")
  })
})
