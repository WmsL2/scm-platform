import { http } from "../shared/http/runtime"
import type { RecommendationConfirmationUpdate, RecommendationRun } from "../types/recommendation"

const base = "/api/v1/recommendations"

export const recommendationApi = {
  detail(projectId: string): Promise<RecommendationRun | null> {
    return http.get(`${base}/projects/${projectId}`)
  },
  start(projectId: string): Promise<RecommendationRun> {
    return http.post(`${base}/runs`, { project_id: projectId })
  },
  cancel(runId: string): Promise<RecommendationRun> {
    return http.post(`${base}/runs/${runId}/cancel`)
  },
  confirm(candidateId: string, body: RecommendationConfirmationUpdate): Promise<RecommendationRun> {
    return http.patch(`${base}/candidates/${candidateId}/confirmation`, body)
  },
  export(runId: string): Promise<Blob> {
    return http.postBlob(`${base}/runs/${runId}/export`, undefined, { timeoutMs: 300_000 })
  },
}
