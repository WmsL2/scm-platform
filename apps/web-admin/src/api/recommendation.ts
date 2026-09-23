import { http } from "../shared/http/runtime"
import type {
  ParsedRequirement,
  RecommendationCandidate,
  RecommendationConfirmationUpdate,
  RecommendationRun,
  RecommendationRunStatus,
} from "../types/recommendation"

const base = "/api/v1/recommendation-projects"

interface CoreRun {
  id: string
  project_id: string
  status: RecommendationRunStatus
  raw_requirement_snapshot: string
  parsed_requirement: ParsedRequirement | null
  provider: string | null
  model: string | null
  prompt_version: string | null
  error: string | null
  created_at: string
  updated_at: string
}

interface CoreCandidate {
  id: string
  run_id: string
  product_id: string
  rank: number
  score: string | null
  reason: string | null
  product_snapshot: Record<string, unknown>
  supplier_snapshot: Record<string, unknown>
  price_snapshot: Record<string, unknown>
  confirmation_id: string | null
}

interface CoreConfirmation {
  id: string
  campaign_price: string | null
  delivery_status: string | null
  inventory_status: string | null
  fulfillment_cycle: string | null
  evidence: string | null
  confirmed_by: string | null
  confirmed_at: string | null
}

function adaptRun(run: CoreRun, candidates: CoreCandidate[] = []): RecommendationRun {
  return {
    ...run,
    category_choices: [],
    candidates: candidates.map((candidate): RecommendationCandidate => ({
      ...candidate,
      confirmation: candidate.confirmation_id ? {
        id: candidate.confirmation_id,
        campaign_price: null,
        fulfillment: null,
        evidence: null,
        confirmed_by: null,
        confirmed_at: null,
      } : null,
    })),
  }
}

async function loadRun(runId: string): Promise<RecommendationRun> {
  const run = await http.get<CoreRun>(`${base}/runs/${runId}`)
  const candidates = await http.get<CoreCandidate[]>(`${base}/runs/${runId}/candidates`)
  return adaptRun(run, candidates)
}

export const recommendationApi = {
  async runs(projectId: string): Promise<RecommendationRun[]> {
    const runs = await http.get<CoreRun[]>(`${base}/${projectId}/runs`)
    return runs.map((run) => adaptRun(run))
  },
  async run(runId: string): Promise<RecommendationRun> {
    return loadRun(runId)
  },
  async detail(projectId: string): Promise<RecommendationRun | null> {
    const runs = await http.get<CoreRun[]>(`${base}/${projectId}/runs`)
    const latest = runs[0]
    if (!latest) return null
    return loadRun(latest.id)
  },
  async start(projectId: string): Promise<RecommendationRun> {
    return adaptRun(
      await http.post<CoreRun>(`${base}/${projectId}/runs`, undefined, { timeoutMs: 300_000 }),
    )
  },
  confirm(candidateId: string, body: RecommendationConfirmationUpdate): Promise<CoreConfirmation> {
    return http.patch(`${base}/candidates/${candidateId}/confirmation`, body)
  },
  confirmMany(runId: string, candidateIds: string[]): Promise<CoreConfirmation[]> {
    return http.post(`${base}/runs/${runId}/confirmations`, { candidate_ids: candidateIds })
  },
}
