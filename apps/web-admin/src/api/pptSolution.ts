import { http } from "../shared/http/runtime"
import type { PptGenerationTask, PptPackage, PptPackageItemInput, PptPriceBandAvailability, PptRecommendationConfig, PptRecommendationMode, PptPriceBand, PptSolutionPlan } from "../types/pptSolution"

const base = "/api/v1/ppt-solution-projects"

export const pptSolutionApi = {
  config(projectId: string): Promise<PptRecommendationConfig | null> { return http.get(`${base}/${projectId}/recommendation-config`) },
  saveConfig(projectId: string, body: { recommendation_mode: PptRecommendationMode; price_bands: PptPriceBand[]; candidate_count_per_band: number; plan_count_per_band: number; fulfillment_deadline: string | null }): Promise<PptRecommendationConfig> { return http.put(`${base}/${projectId}/recommendation-config`, body) },
  plans(runId: string): Promise<PptSolutionPlan[]> {
    return http.get(`${base}/runs/${runId}/plans`)
  },
  selectPlan(planId: string): Promise<PptSolutionPlan> {
    return http.post(`${base}/plans/${planId}/select`)
  },
  planAvailability(runId: string): Promise<PptPriceBandAvailability[]> {
    return http.get(`${base}/runs/${runId}/plan-availability`)
  },
  packages(runId: string): Promise<PptPackage[]> {
    return http.get(`${base}/runs/${runId}/packages`)
  },
  createPackage(runId: string, body: { name: string; price_tier?: string | null; reason?: string | null; items: PptPackageItemInput[] }): Promise<PptPackage> {
    return http.post(`${base}/runs/${runId}/packages`, body)
  },
  removePackage(packageId: string): Promise<boolean> {
    return http.delete(`${base}/packages/${packageId}`)
  },
  generations(projectId: string): Promise<PptGenerationTask[]> {
    return http.get(`${base}/${projectId}/generations`)
  },
  generate(projectId: string, runId: string): Promise<PptGenerationTask> {
    return http.post(`${base}/${projectId}/runs/${runId}/generations`, {
      use_default_template: true,
    }, { timeoutMs: 1_800_000 })
  },
  download(taskId: string, fileId: string): Promise<Blob> {
    return http.getBlob(`${base}/generations/${taskId}/files/${fileId}/download`, { timeoutMs: 300_000 })
  },
}
