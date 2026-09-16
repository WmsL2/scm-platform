import { http } from "../shared/http/runtime"
import type { DashboardSummary } from "../types/dashboard"

export const dashboardApi = {
  summary(): Promise<DashboardSummary> {
    return http.get<DashboardSummary>("/api/v1/dashboard/summary")
  },
}
