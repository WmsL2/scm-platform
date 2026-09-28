import { http } from "../shared/http/runtime"
import type { PptGenerationTask, PptPackage, PptPackageItemInput } from "../types/pptSolution"

const base = "/api/v1/ppt-solution-projects"

export const pptSolutionApi = {
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
  generate(projectId: string, runId: string, useDefaultTemplate: boolean): Promise<PptGenerationTask> {
    return http.post(`${base}/${projectId}/runs/${runId}/generations`, {
      use_default_template: useDefaultTemplate,
    }, { timeoutMs: 1_800_000 })
  },
  download(taskId: string, fileId: string): Promise<Blob> {
    return http.getBlob(`${base}/generations/${taskId}/files/${fileId}/download`, { timeoutMs: 300_000 })
  },
}
