import { http } from "../shared/http/runtime"
import type {
  FactoryDirectStatus,
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
  factory_direct: FactoryDirectStatus | null
  confirmation: CoreConfirmation | null
}

interface CoreConfirmation {
  id: string
  candidate_id: string
  campaign_price: string | null
  delivery_status: string | null
  inventory_status: string | null
  factory_direct: FactoryDirectStatus
  fulfillment_cycle: string | null
  evidence: string | null
  confirmed_by: string | null
  confirmed_at: string | null
  updated_at: string
}

function adaptRun(run: CoreRun, candidates: CoreCandidate[] = []): RecommendationRun {
  return {
    ...run,
    category_choices: [],
    candidates: candidates.map((candidate): RecommendationCandidate => ({
      ...candidate,
      confirmation: candidate.confirmation,
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
  export(projectId: string, runId: string): Promise<{ id: string; original_filename: string }> {
    return http.post(`${base}/${projectId}/runs/${runId}/exports`)
  },
  downloadExport(runId: string, fileId: string): Promise<Blob> {
    return http.getBlob(`${base}/runs/${runId}/exports/${fileId}/download`)
  },
}
