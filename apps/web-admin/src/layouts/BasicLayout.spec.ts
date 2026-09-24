import { describe, expect, it } from "vitest"

import source from "./BasicLayout.vue?raw"

describe("BasicLayout pending badges", () => {
  it("only shows an actionable pending count on the supplier menu", () => {
    expect(source).toContain("dashboard.pendingSupplierCount")
    expect(source).not.toContain("dashboard.pendingProductImportCount")
    expect(source).not.toContain("dashboard.pendingProjectActionCount")
    expect(source).toContain('<template #title>工作台</template>')
    expect(source).toContain('<template #title>商品主数据</template>')
    expect(source).toContain('<template #title>投标项目</template>')
  })
})
