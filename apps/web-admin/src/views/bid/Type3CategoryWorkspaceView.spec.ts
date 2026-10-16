import { describe, expect, it } from "vitest"
import source from "./Type3CategoryWorkspaceView.vue?raw"

describe("Type3CategoryWorkspaceView", () => {
  it("keeps selection adjustment and frozen candidate details in the Type-3 workspace", () => {
    expect(source).toContain("返回调整选品")
    expect(source).toContain("批量撤销确认")
    expect(source).toContain("unconfirmCandidates")
    expect(source).toContain("type3RecommendationApi.run(runId)")
    expect(source).toContain("before calculating an all-scope selection")
    expect(source).toContain("候选商品详情（本次冻结快照）")
    expect(source).toContain("不会因后续商品主数据修改而变化")
    expect(source).toContain("当前商品范围和所选 Sheet/类目下没有候选商品")
    expect(source).toContain("当前显示的是最新一次生成结果")
    expect(source).toContain("自定义显示列")
    expect(source).toContain("scm.type3-candidates.visible-columns.v1")
    expect(source).toContain("visibleCandidateColumns")
    expect(source).toContain("candidateColumnValue")
    expect(source).toContain("来源 Sheet 固定显示")
  })
})
