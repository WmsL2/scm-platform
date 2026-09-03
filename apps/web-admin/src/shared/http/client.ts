export interface ApiResponse<T> {
  code: string
  message: string
  data: T
  request_id?: string
}

export interface ErrorResponse {
  code: string
  message: string
  request_id?: string
}

export class HttpError extends Error {
  constructor(readonly status: number, readonly response: ErrorResponse) {
    super(response.message)
  }
}

export interface HttpClientOptions {
  baseUrl?: string
  timeoutMs?: number
  getAuthorization?: () => string | undefined
  onUnauthorized?: () => void
  onForbidden?: () => void
}

export class HttpClient {
  constructor(private readonly options: HttpClientOptions = {}) {}

  async get<T>(path: string, requestId = crypto.randomUUID()): Promise<T> {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), this.options.timeoutMs ?? 10_000)
    try {
      const authorization = this.options.getAuthorization?.()
      const response = await fetch(`${this.options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"}${path}`, {
        headers: { Accept: "application/json", ...(authorization ? { Authorization: authorization } : {}), "X-Request-ID": requestId },
        signal: controller.signal,
      })
      const body = (await response.json()) as ApiResponse<T> | ErrorResponse
      if (response.status === 401) this.options.onUnauthorized?.()
      if (response.status === 403) this.options.onForbidden?.()
      if (!response.ok) throw new HttpError(response.status, body as ErrorResponse)
      const envelope = body as ApiResponse<T>
      if (envelope.code !== "OK") throw new HttpError(400, envelope)
      return envelope.data
    } finally {
      clearTimeout(timeout)
    }
  }
}

export const http = new HttpClient()
