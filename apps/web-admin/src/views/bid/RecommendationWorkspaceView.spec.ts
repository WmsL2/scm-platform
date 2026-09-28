import { flushPromises, mount } from "@vue/test-utils"
import ElementPlus from "element-plus"
import { createPinia } from "pinia"
import { afterEach, describe, expect, it, vi } from "vitest"
import RecommendationWorkspaceView from "./RecommendationWorkspaceView.vue"
import source from "./RecommendationWorkspaceView.vue?raw"

const recommendationApi = vi.hoisted(() => ({ runs: vi.fn(), run: vi.fn(), confirm: vi.fn(), removeConfirmation: vi.fn(), confirmMany: vi.fn(), completeSelection: vi.fn(), reopenSelection: vi.fn(), start: vi.fn(), export: vi.fn(), downloadExport: vi.fn() }))
const bidApi = vi.hoisted(() => ({ get: vi.fn(), recommendationTemplates: vi.fn(), recommendationTemplateMapping: vi.fn(), recommendationTemplateStructure: vi.fn(), updateRecommendationTemplateMapping: vi.fn(), update: vi.fn(), submit: vi.fn(), win: vi.fn(), lose: vi.fn() }))
vi.mock("../../api/recommendation", () => ({ recommendationApi }))
vi.mock("../../api/bid", () => ({ bidApi }))
vi.mock("../../stores/auth", () => ({ useAuthStore: () => ({ hasPermission: () => true }) }))
vi.mock("vue-router", () => ({ useRoute: () => ({ params: { id: "project-1" } }), useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }))

const project = { id: "project-1", project_name: "自由推品测试", project_type: "FREE_RECOMMENDATION", status: "SELECTING", files: [], remark: "一段足够长的自由推品需求说明，用于真实组件挂载测试。" }
const candidate = {
  id: "candidate-1", product_id: "product-1", rank: 1, score: "90", reason: "适合活动场景",
  // A historical pending flag must be ignored by the new UI flow.
  manual_flags: { checks: [{ code: "DROP_SHIPPING", required: true, status: "PENDING" }] },
  product_snapshot: { product_name: "测试商品", brand: "品牌" }, supplier_snapshot: {},
  price_snapshot: { agreement_price: "99", discount_rate: "0.75", gross_margin: "0.06" }, factory_direct: null, confirmation: null,
}

function configure() {
  const run = {
    id: "run-1", project_id: "project-1", status: "WAITING_CONFIRMATION", progress_percent: 100,
    progress_message: null, raw_requirement_snapshot: project.remark,
    parsed_requirement: { gross_margin_min: "0.06", jd_price_min: null, jd_price_max: null, category_keywords: ["食品"], brand_keywords: [], scenario_keywords: [], fulfillment_mode: "DROP_SHIPPING", agreement_price_max: "200", discount_rate_max: "0.8", scenarios: ["中秋"] },
    provider: "fake", model: "fake", prompt_version: "test", error: null, category_choices: [], candidates: [candidate], created_at: "2026-09-24T00:00:00", updated_at: "2026-09-24T00:00:00",
  }
  bidApi.get.mockResolvedValue(project)
  bidApi.recommendationTemplates.mockResolvedValue([])
  recommendationApi.runs.mockResolvedValue([run])
  recommendationApi.run.mockResolvedValue(run)
  recommendationApi.confirm.mockResolvedValue({ id: "confirmation-1" })
  recommendationApi.confirmMany.mockResolvedValue([{ id: "confirmation-1" }])
}

async function mountWorkspace() {
  configure()
  const wrapper = mount(RecommendationWorkspaceView, {
    global: { plugins: [createPinia(), ElementPlus], stubs: { ElDialog: { props: ["modelValue"], template: '<div v-if="modelValue" class="dialog"><slot /><slot name="footer" /></div>' } } },
  })
  await flushPromises()
  return wrapper
}

afterEach(() => vi.clearAllMocks())

describe("RecommendationWorkspaceView", () => {
  it("renders core price fields and marks non-price information as reference", async () => {
    const wrapper = await mountWorkspace()
    expect(wrapper.text()).toContain("筛选：协议价")
    expect(wrapper.text()).toContain("参考：场景")
    expect(wrapper.text()).toContain("折扣率")
    expect(wrapper.text()).toContain("点位")
    expect(wrapper.text()).not.toContain("人工核验")
  })

  it("allows a historical pending manual flag to enter the direct selection flow", async () => {
    const wrapper = await mountWorkspace()
    wrapper.findComponent({ name: "ElTable" }).vm.$emit("row-click", candidate)
    await flushPromises()
    await wrapper.findAll("button").find((item) => item.text().includes("加入人工选品"))!.trigger("click")
    expect(recommendationApi.confirm).toHaveBeenCalledWith("candidate-1", expect.any(Object))
  })

  it("allows the same historical candidate to be batch-confirmed", async () => {
    const wrapper = await mountWorkspace()
    wrapper.findComponent({ name: "ElTable" }).vm.$emit("selection-change", [candidate])
    await flushPromises()
    await wrapper.findAll("button").find((item) => item.text().includes("批量加入"))!.trigger("click")
    expect(recommendationApi.confirmMany).toHaveBeenCalledWith("run-1", ["candidate-1"])
  })

  it("retains no manual API or checkbox gate in the workspace source", () => {
    expect(source).not.toContain("updateManualChecks")
    expect(source).not.toContain("manualChecksPassed")
    expect(source).toContain("confirmMany")
  })
})
