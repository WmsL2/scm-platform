import { flushPromises, mount } from "@vue/test-utils"
import ElementPlus, { ElMessage, ElSelect } from "element-plus"
import { createPinia } from "pinia"
import { afterEach, describe, expect, it, vi } from "vitest"
import { HttpError } from "../../shared/http"
import RecommendationWorkspaceView from "./RecommendationWorkspaceView.vue"
import source from "./RecommendationWorkspaceView.vue?raw"

const recommendationApi = vi.hoisted(() => ({ runs: vi.fn(), run: vi.fn(), updateManualChecks: vi.fn(), confirm: vi.fn(), confirmMany: vi.fn(), start: vi.fn(), export: vi.fn(), downloadExport: vi.fn() }))
const bidApi = vi.hoisted(() => ({ get: vi.fn(), recommendationTemplates: vi.fn(), recommendationTemplateMapping: vi.fn(), recommendationTemplateStructure: vi.fn(), updateRecommendationTemplateMapping: vi.fn(), update: vi.fn() }))
const messages = vi.hoisted(() => ({ warning: vi.fn(), success: vi.fn(), error: vi.fn() }))

vi.mock("../../api/recommendation", () => ({ recommendationApi }))
vi.mock("../../api/bid", () => ({ bidApi }))
vi.mock("../../stores/auth", () => ({ useAuthStore: () => ({ hasPermission: () => true }) }))
vi.mock("vue-router", () => ({ useRoute: () => ({ params: { id: "project-1" } }), useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }))
vi.mock("element-plus", async (importOriginal) => {
  const actual = await importOriginal<typeof import("element-plus")>()
  return { ...actual, ElMessage: messages }
})

const project = { id: "project-1", project_code: "REC-1", project_name: "自由推品测试", buyer_name: "客户", status: "IMPORTED", import_status: "NOT_REQUIRED", project_type: "FREE_RECOMMENDATION", total_item_count: 0, processed_item_count: 0, remark: "一段足够长的自由推品需求说明，用于真实组件挂载测试。", template_id: null, template_version: null, import_error: null, submitted_file_id: null, files: [], events: [], created_at: "2026-09-24T00:00:00" } as const

function candidate(manualFlags: Record<string, unknown> | null, confirmation: Record<string, unknown> | null = null) {
  return { id: "candidate-1", product_id: "product-1", rank: 1, score: "90", reason: "适合活动场景", manual_flags: manualFlags, product_snapshot: { product_name: "测试商品", brand: "品牌" }, supplier_snapshot: {}, price_snapshot: { agreement_price: "99", gross_margin: "0.06" }, factory_direct: null, confirmation }
}

function configure(candidateValue: Record<string, unknown>, parsedRequirement: Record<string, unknown> | null = null) {
  const run = { id: "run-1", project_id: "project-1", status: "WAITING_CONFIRMATION", progress_percent: 100, progress_message: null, raw_requirement_snapshot: project.remark, parsed_requirement: parsedRequirement, provider: "fake", model: "fake", prompt_version: "test", error: null, category_choices: [], candidates: [candidateValue], created_at: "2026-09-24T00:00:00", updated_at: "2026-09-24T00:00:00" }
  bidApi.get.mockResolvedValue(project)
  bidApi.recommendationTemplates.mockResolvedValue([])
  recommendationApi.runs.mockResolvedValue([run])
  recommendationApi.run.mockResolvedValue(run)
  recommendationApi.updateManualChecks.mockResolvedValue(candidateValue)
  recommendationApi.confirm.mockResolvedValue({ id: "confirmation-1" })
}

async function mountWorkspace() {
  const wrapper = mount(RecommendationWorkspaceView, {
    global: { plugins: [createPinia(), ElementPlus], stubs: { ElDialog: { props: ["modelValue"], template: '<div v-if="modelValue" class="dialog"><slot /><slot name="footer" /></div>' } } },
  })
  await flushPromises()
  return wrapper
}

async function openConfirmation(wrapper: Awaited<ReturnType<typeof mountWorkspace>>) {
  const button = wrapper.findAll("button").find((item) => item.text().includes("确认选品"))
  expect(button).toBeDefined()
  await button!.trigger("click")
  await flushPromises()
}

afterEach(() => { vi.clearAllMocks(); document.body.innerHTML = "" })

describe("RecommendationWorkspaceView", () => {
  it("renders a pending required manual check from the API", async () => {
    configure(candidate({ checks: [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "PENDING", evidence: null }] }))
    const wrapper = await mountWorkspace()
    expect(wrapper.text()).toContain("必填")
    expect(wrapper.text()).toContain("是否支持一件代发：待确认")
    expect(wrapper.text()).toContain("必填 1 项未完成")
  })

  it("saves PASS and evidence through the manual-check API", async () => {
    configure(candidate({ checks: [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "PENDING", evidence: null }] }))
    const wrapper = await mountWorkspace()
    await openConfirmation(wrapper)
    await wrapper.find(".dialog").findAllComponents(ElSelect)[0].vm.$emit("update:modelValue", "PASS")
    await wrapper.get('input[placeholder="核验依据，例如供应商微信确认"]').setValue("供应商确认支持一件代发")
    await wrapper.findAll("button").find((item) => item.text().includes("保存人工核验"))!.trigger("click")
    await flushPromises()
    expect(recommendationApi.updateManualChecks).toHaveBeenCalledWith("candidate-1", [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "PASS", evidence: "供应商确认支持一件代发" }])
  })

  it("blocks confirmation in the UI while a required check is pending", async () => {
    configure(candidate({ checks: [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "PENDING", evidence: null }] }))
    const wrapper = await mountWorkspace()
    await openConfirmation(wrapper)
    await wrapper.findAll("button").find((item) => item.text().includes("确认保存"))!.trigger("click")
    expect(recommendationApi.confirm).not.toHaveBeenCalled()
    expect(messages.warning).toHaveBeenCalledWith("仍有必填人工核验项未完成")
  })

  it("summarizes passed and failed required checks for batch selection", async () => {
    configure(candidate({ checks: [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "PASS", evidence: "供应商确认" }] }))
    const passed = await mountWorkspace()
    expect(passed.text()).toContain("必填核验已完成")
    expect(passed.findAll('input[type="checkbox"]').some((item) => !item.attributes("disabled"))).toBe(true)

    configure(candidate({ checks: [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "FAIL", evidence: "供应商不支持" }] }))
    const failed = await mountWorkspace()
    expect(failed.text()).toContain("是否支持一件代发：不满足")
    expect(failed.text()).toContain("必填 1 项未通过")
    expect(failed.text()).toContain("请先完成必填人工核验")
  })

  it("defends bulk confirmation when a stale pending candidate is selected", async () => {
    const candidateValue = candidate({ checks: [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "PENDING", evidence: null }] })
    configure(candidateValue)
    const wrapper = await mountWorkspace()
    await wrapper.findComponent({ name: "ElTable" }).vm.$emit("selection-change", [candidateValue])
    await wrapper.findAll("button").find((item) => item.text().includes("批量确认选中"))!.trigger("click")
    expect(recommendationApi.confirmMany).not.toHaveBeenCalled()
    expect(messages.warning).toHaveBeenCalledWith("选中商品中仍有必填人工核验项未完成")
  })

  it("persists passing manual checks before confirming a candidate", async () => {
    configure(candidate({ checks: [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "PENDING", evidence: null }] }))
    const wrapper = await mountWorkspace()
    await openConfirmation(wrapper)
    await wrapper.find(".dialog").findAllComponents(ElSelect)[0].vm.$emit("update:modelValue", "PASS")
    await wrapper.get('input[placeholder="核验依据，例如供应商微信确认"]').setValue("供应商确认支持一件代发")
    await wrapper.findAll("button").find((item) => item.text().includes("确认保存"))!.trigger("click")
    await flushPromises()
    expect(recommendationApi.updateManualChecks.mock.invocationCallOrder[0]).toBeLessThan(
      recommendationApi.confirm.mock.invocationCallOrder[0],
    )
    expect(recommendationApi.confirm).toHaveBeenCalledWith("candidate-1", expect.any(Object))
  })

  it("does not confirm after a manual-check PATCH failure", async () => {
    configure(candidate({ checks: [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "PASS", evidence: "供应商确认" }] }))
    recommendationApi.updateManualChecks.mockRejectedValue(new HttpError(409, { code: "LOCKED", message: "核验已锁定" }))
    const wrapper = await mountWorkspace()
    await openConfirmation(wrapper)
    await wrapper.findAll("button").find((item) => item.text().includes("确认保存"))!.trigger("click")
    await flushPromises()
    expect(recommendationApi.confirm).not.toHaveBeenCalled()
    expect(messages.error).toHaveBeenCalledWith("核验已锁定")
  })

  it("shows confirmation PATCH errors after successful manual-check persistence", async () => {
    configure(candidate({ checks: [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "PASS", evidence: "供应商确认" }] }))
    recommendationApi.confirm.mockRejectedValue(new HttpError(409, { code: "INELIGIBLE", message: "候选商品当前不可用" }))
    const wrapper = await mountWorkspace()
    await openConfirmation(wrapper)
    await wrapper.findAll("button").find((item) => item.text().includes("确认保存"))!.trigger("click")
    await flushPromises()
    expect(recommendationApi.updateManualChecks).toHaveBeenCalled()
    expect(messages.error).toHaveBeenCalledWith("候选商品当前不可用")
    expect(messages.success).not.toHaveBeenCalledWith("人工确认已保存")
  })

  it("keeps confirmed candidates out of batch selection", async () => {
    configure(candidate(null, { id: "confirmation-1" }))
    const wrapper = await mountWorkspace()
    expect(wrapper.text()).toContain("已确认")
    expect(wrapper.findAll('input[type="checkbox"]').at(-1)?.attributes("disabled")).toBeDefined()
  })

  it("shows the server 409 message without a false success", async () => {
    configure(candidate({ checks: [{ code: "DROP_SHIPPING", label: "是否支持一件代发", requirement_text: "一件代发", required: true, status: "PASS", evidence: "已确认" }] }))
    recommendationApi.updateManualChecks.mockRejectedValue(new HttpError(409, { code: "RECOMMENDATION_MANUAL_CHECK_CONFIRMED_LOCKED", message: "已确认候选的必填人工核验不能降级" }))
    const wrapper = await mountWorkspace()
    await openConfirmation(wrapper)
    await wrapper.find(".dialog").findAllComponents(ElSelect)[0].vm.$emit("update:modelValue", "FAIL")
    await wrapper.findAll("button").find((item) => item.text().includes("保存人工核验"))!.trigger("click")
    await flushPromises()
    expect(messages.error).toHaveBeenCalledWith("已确认候选的必填人工核验不能降级")
    expect(messages.success).not.toHaveBeenCalledWith("人工核验已保存")
  })

  it.each([null, {}])("renders legacy manual_flags=%j and still opens confirmation", async (manualFlags) => {
    configure(candidate(manualFlags))
    const wrapper = await mountWorkspace()
    expect(wrapper.text()).not.toContain("是否支持一件代发")
    await openConfirmation(wrapper)
    expect(wrapper.find(".dialog").exists()).toBe(true)
  })

  it("renders a historical parsed requirement without V2 fields", async () => {
    configure(candidate(null), { gross_margin_min: "0.06", jd_price_min: null, jd_price_max: null, category_keywords: [], brand_keywords: [], scenario_keywords: [], fulfillment_mode: null })
    const wrapper = await mountWorkspace()
    expect(wrapper.text()).toContain("需求理解")
    expect(wrapper.text()).toContain("0.06")
  })

  it("renders the currently displayed V2 scenario and preferred-brand fields", async () => {
    configure(candidate(null), { gross_margin_min: "0.06", jd_price_min: null, jd_price_max: null, category_keywords: [], brand_keywords: [], scenario_keywords: [], fulfillment_mode: null, scenarios: ["中秋", "国庆"], promotion_preference: "SPECIAL_PRICE", demand_mode: "REDEMPTION", preferred_brands: ["华为"] })
    const wrapper = await mountWorkspace()
    expect(wrapper.text()).toContain("中秋、国庆")
    expect(wrapper.text()).toContain("华为")
  })

  it("keeps the existing source-level contracts", () => {
    expect(source).toContain("recommendationTemplateStructure")
    expect(source).toContain("selectedMappingJson")
    expect(source).toContain("保存补充说明并重新生成")
  })
})
