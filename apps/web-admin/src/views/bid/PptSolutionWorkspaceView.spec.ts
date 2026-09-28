import { describe, expect, it } from "vitest"
import source from "./PptSolutionWorkspaceView.vue?raw"

describe("PptSolutionWorkspaceView", () => {
  it("keeps AI recommendation, human confirmation, bundling and PPT generation explicit", () => {
    expect(source).toContain("AI 推荐候选")
    expect(source).toContain("人工已选商品")
    expect(source).toContain("组成套装")
    expect(source).toContain("套装总价不能超过价格档位")
    expect(source).toContain("使用系统默认模板生成")
    expect(source).toContain("下载 PPTX")
  })
})
